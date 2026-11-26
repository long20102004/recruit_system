"""Bo dich vu dung chung cho API va `run-e2e`: nap config, KB snapshot, encoder, `CvIndex` MOT lan.

- Moi thao tac dung chi muc RAM hoac encoder (nap CV/JD, xoa CV, match) chay duoi MOT khoa
  (`CvIndex`, encoder GPU va ket noi cache BERTScore khong an toan khi dung song song).
- Su kien `cv_committed` -> `CvIndex.add`; `cv_deleted` -> go khoi RAM + xoa cache BERTScore.
- Explain chi doc / ghi Postgres nen khong can khoa.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from cvmatch.api.logjson import Timer, log_event
from cvmatch.api.rwlock import RWLock
from cvmatch.api.warmup import cv_texts, jd_texts, precompute
from cvmatch.core import events
from cvmatch.core.config import AppConfig, load_config
from cvmatch.core.db import connect, db_url
from cvmatch.core.kb.matcher import SkillMatcher
from cvmatch.core.kb.snapshot import KBSnapshot
from cvmatch.core.kb.store import load_snapshot_db
from cvmatch.core.models import Encoder, FakeEncoder, get_encoder
from cvmatch.explain.service import ExplainService, band_of
from cvmatch.ingest.cv.record import CvContext
from cvmatch.ingest.cv.service import CvIngestor, IngestOutcome, delete_cv
from cvmatch.ingest.jd.pipeline import JdIngestor, JdOutcome, set_jd_status
from cvmatch.rerank.bertscore.cache import TokenCache
from cvmatch.rerank.bertscore.engine import BertScorer
from cvmatch.rerank.run import Reranker
from cvmatch.retrieve.jd_to_cvs import retrieve_for_jd
from cvmatch.retrieve.cv_to_jds import retrieve_for_cv
from cvmatch.retrieve.index import CvIndex
from cvmatch.retrieve.jd_index import JdIndex


def config_and_encoder(config_dir=None, *, fake: bool | None = None, overrides: dict | None = None,
                       ) -> tuple[AppConfig, Encoder | None]:
    """Config + encoder phu hop. FakeEncoder: khoa `embed_model` doi thanh `fake-...` (khong lan voi
    vector that trong cung DB). Encoder that tra None (nap luoi trong Services)."""
    if fake is None:
        fake = os.environ.get("CVMATCH_FAKE_ENCODER", "0") == "1"
    ov = dict(overrides or {})
    if not fake:
        return load_config(config_dir, overrides=ov or None), None
    base = load_config(config_dir, overrides=ov or None)
    key = base.models.embed.key
    key = key if key.startswith("fake-") else f"fake-{key}"
    ov.setdefault("models", {}).setdefault("embed", {})["key"] = key
    cfg = load_config(config_dir, overrides=ov)
    return cfg, FakeEncoder(dim=cfg.models.embed.dim, key=key)


@dataclass
class MatchOutcome:
    run_id: str                       # rerank run (dung cho explain)
    retrieve_run_id: str
    jd_id: str
    jd_version: int
    n_pool: int
    items: list[dict]                 # top N: cv_id, rank, score, band, cap_applied, flags
    warnings: list[dict]
    timings: dict[str, float]
    retrieve_top: list[dict] = field(default_factory=list)   # top theo `fused` (R-A0, khong rerank)
    final_items: list = field(default_factory=list)          # FinalItem day du (run-e2e in bao cao)


class Services:
    def __init__(self, cfg: AppConfig, *, url: str | None = None, encoder: Encoder | None = None,
                 snapshot: KBSnapshot | None = None, hmac_key: str | None = None, db_cache: bool = True,
                 bm25_rebuild_growth: float = 0.10, precompute_tokens: bool | None = None,
                 bm25_rebuild_max_age_s: float = 24 * 3600):
        self.url = url or db_url()
        # CV them tang dan dung tu vung / IDF cua lan dung BM25 truoc (T08) -> tu moi khong duoc cham.
        # Kho tang qua ti le nay (hoac luc dung kho rong) thi dung lai BM25 ngay sau lo nap.
        self.bm25_rebuild_growth = bm25_rebuild_growth
        self.bm25_rebuild_max_age_s = bm25_rebuild_max_age_s
        # S05 / V-11: match, explain chay song song (khoa doc); nap / xoa / doi trang thai doc quyen (khoa ghi)
        self.lock = RWLock()
        # S05 / V-12: tinh san token BERTScore khi nap (mac dinh bat; tat bang CVMATCH_PRECOMPUTE_TOKENS=0)
        self.precompute_tokens = (os.environ.get("CVMATCH_PRECOMPUTE_TOKENS", "1") == "1"
                                  if precompute_tokens is None else precompute_tokens)
        self.warm_status: dict = {"state": "idle"}
        self.timings: dict[str, float] = {}
        with connect(self.url) as conn:
            snap = snapshot or load_snapshot_db(conn, cfg.ontology_version)
            if cfg.ontology_version != snap.ontology_version:      # None -> ban nap gan nhat
                cfg = cfg.model_copy(update={"ontology_version": snap.ontology_version})
            self.cfg, self.snapshot = cfg, snap
            with Timer() as t:
                self.encoder = encoder or get_encoder(cfg, fake=False)
            self.timings["load_encoder_s"] = t.s
            with Timer() as t:
                self.index = CvIndex(cfg).build(conn)
            self.timings["index_build_s"] = t.s
            self._bm25_built_at, self._bm25_active_at_build = time.monotonic(), int(self.index.active.sum())
            with Timer() as t:
                self.jd_index = JdIndex(cfg).build(conn)
            self.timings["jd_index_build_s"] = t.s
        self._suppress_index = False         # CV tam (Luong D xem truoc): khong vao CvIndex
        self.ctx = CvContext.create(cfg, snap, hmac_key=hmac_key)
        self._cache_conn = connect(self.url) if db_cache else None
        cache = TokenCache(cfg.bertscore.key(), conn=self._cache_conn)
        self.scorer = BertScorer(self.encoder, cfg.bertscore, SkillMatcher(snap), cache)
        self.reranker = Reranker(cfg, self.scorer, snap)
        self.explainer = ExplainService(cfg, snap)
        self._handlers = [("cv_committed", self._on_cv_committed), ("cv_deleted", self._on_cv_deleted),
                          ("jd_committed", self._on_jd_changed), ("jd_status_changed", self._on_jd_changed)]
        for ev, h in self._handlers:
            events.on(ev, h)
        log_event("services_ready", ontology_version=snap.ontology_version, embed_model=self.encoder.key(),
                  n_cv=int(self.index.active.sum()), **self.timings)

    # ----------------------------------------------------------------- vong doi

    def connect(self):
        return connect(self.url)

    def close(self) -> None:
        for ev, h in self._handlers:
            events.off(ev, h)
        self._handlers = []
        if self._cache_conn is not None:
            self._cache_conn.close()
            self._cache_conn = None

    def __enter__(self) -> "Services":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _on_jd_changed(self, _ev) -> None:
        with self.connect() as conn:
            self.jd_index.build(conn)

    def _on_cv_committed(self, ev: events.CvCommitted) -> None:
        if self._suppress_index:
            return
        with self.connect() as conn:
            self.index.add(conn, [ev.cv_id], [ev.replaced_cv_id] if ev.replaced_cv_id else None)

    def _on_cv_deleted(self, ev: events.CvDeleted) -> None:
        self.index.deactivate(ev.cv_id)
        if ev.bullet_texts_raw:
            self.scorer.purge_texts(list(ev.bullet_texts_raw))

    # ----------------------------------------------------------------- Tang 0

    def ingest_cvs(self, items: list[tuple[str, Any]], *, batch_size: int = 32) -> list[IngestOutcome]:
        with self.lock.write(), self.connect() as conn, Timer() as t:
            out = CvIngestor(conn, self.ctx, self.encoder, batch_size=batch_size).ingest_many(items)
            rebuilt = self._maybe_rebuild_bm25(conn)
            n_tok = 0
            if self.precompute_tokens and not self._suppress_index:
                n_tok = precompute(self.scorer, cv_texts(conn, [o.cv_id for o in out if o.status == "ok"]))
        log_event("ingest_cv", n=len(items), ok=sum(o.status == "ok" for o in out), bm25_rebuilt=rebuilt,
                  token_texts=n_tok, duration_s=t.s)
        return out

    def _maybe_rebuild_bm25(self, conn) -> bool:
        """V-13: dung lai BM25 (IDF moi) khi so CV THAY DOI (them hoac xoa) qua `bm25_rebuild_growth` so voi luc
        dung, hoac lan dung da qua `bm25_rebuild_max_age_s`."""
        now = int(self.index.active.sum())               # CV dang dung (xoa / ban cu da tat)
        built, added = self._bm25_active_at_build, self.index.n_cv - self.index.bm25.n_docs_at_build
        changed = (added + abs(now - added - built) > built * self.bm25_rebuild_growth) if built else now > 0
        stale = time.monotonic() - self._bm25_built_at > self.bm25_rebuild_max_age_s and (added or now != built)
        if not (changed or stale):
            return False
        self.index.rebuild_bm25(conn)
        self._bm25_built_at, self._bm25_active_at_build = time.monotonic(), now
        return True

    def warm_cache(self, max_s: float = 600.0, *, chunk: int = 256) -> dict:
        """V-12: tinh san token BERTScore cho JD dang mo + CV trong chi muc (cai da co trong cache DB thi chi doc).
        Chay nen luc khoi dong; moi doan giu khoa doc ngan (match van chay xen ke). Dung khi qua `max_s`."""
        deadline = time.monotonic() + max_s
        self.warm_status = {"state": "running", "texts": 0}
        try:
            with self.lock.read(), self.connect() as conn:
                n = precompute(self.scorer, jd_texts(conn), deadline=deadline)
                ids = [self.index.cv_ids[i] for i in range(len(self.index.cv_ids)) if self.index.active[i]]
            self.warm_status["texts"] = n
            for s in range(0, len(ids), chunk):
                if time.monotonic() > deadline:
                    self.warm_status["state"] = "stopped_time_limit"
                    break
                with self.lock.read(), self.connect() as conn:
                    self.warm_status["texts"] += precompute(self.scorer, cv_texts(conn, ids[s:s + chunk]),
                                                            deadline=deadline)
            else:
                self.warm_status["state"] = "done"
        except Exception as e:  # noqa: BLE001 - lam nong loi khong duoc lam sap API
            self.warm_status = {"state": "error", "error": f"{type(e).__name__}: {e}"}
        log_event("warm_cache", **self.warm_status, cache=self.scorer.cache.stats())
        return self.warm_status

    def ingest_cv(self, raw: Any, source: str = "api") -> IngestOutcome:
        return self.ingest_cvs([(source, raw)])[0]

    def delete_cv(self, cv_id: str) -> bool:
        with self.lock.write(), self.connect() as conn:
            ok = delete_cv(conn, cv_id)
            if ok:
                self._maybe_rebuild_bm25(conn)
        log_event("delete_cv", cv_id=cv_id, found=ok)
        return ok

    def set_recommendable(self, cv_id: str, value: bool) -> list[str] | None:
        """S07: bat / tat nhan goi y cho UNG VIEN cua `cv_id` (moi ban cung candidate_key). None = khong co CV."""
        with self.lock.write(), self.connect() as conn:
            row = conn.execute("SELECT candidate_key FROM cv WHERE cv_id = %s AND status <> 'deleted'",
                               (cv_id,)).fetchone()
            if row is None:
                return None
            ids = [str(r["cv_id"]) for r in conn.execute(
                "UPDATE cv SET recommendable = %s, updated_at = now() WHERE cv_id = %s"
                " OR (candidate_key IS NOT NULL AND candidate_key = %s) RETURNING cv_id",
                (value, cv_id, row["candidate_key"]))]
            self.index.set_recommendable(ids, value)
        log_event("set_recommendable", cv_id=cv_id, value=value, n=len(ids))
        return ids

    def ingest_jd(self, raw: Any, source: str = "api") -> JdOutcome:
        with self.lock.write(), self.connect() as conn, Timer() as t:
            out = JdIngestor(conn, self.ctx, self.encoder).ingest_one(raw, source)
            if self.precompute_tokens and out.status == "ok" and out.version is not None:
                precompute(self.scorer, jd_texts(conn, [(out.jd_id, out.version)]))
        log_event("ingest_jd", jd_id=out.jd_id, version=out.version, status=out.status, duration_s=t.s)
        return out

    def set_jd_status(self, jd_id: str, status: str) -> int | None:
        with self.lock.write(), self.connect() as conn:
            return set_jd_status(conn, jd_id, status)

    # ----------------------------------------------------------------- Tang 1 + 2

    def _norm_filters(self, hf: dict | None) -> dict | None:
        """Dia diem loc cung -> CUNG ma chuan hoa voi cv_meta / jd_meta (A4/B2: "Hà Nội" -> ma tinh)."""
        if not hf:
            return None
        hf = dict(hf)
        if hf.get("location"):
            hf["location"] = self.ctx.locations(hf["location"]) or hf["location"]
        return hf

    def _item_extra(self, it) -> dict:
        """Diem tung feature (0-1, None = thieu / tat) va ky nang dat / gan dung / thieu (ten hien thi cua KB)
        de backend khong phai goi explain cho tung dong."""
        names = self.snapshot.skills
        name = lambda sid: names[sid].name if sid in names else sid  # noqa: E731
        sf = it.skill_facts
        return {"features": it.features.model_dump(),
                "skills": {"met": [name(m.skill) for m in sf.met],
                           "partial": [name(p.required) for p in sf.partial],
                           "missing": [name(s) for s in sf.missing]}}

    def match_jd(self, jd_id: str, *, K: int | None = None, N: int | None = None, hard_filters: dict | None = None,
                 exclude_cv_ids: list[str] | None = None, views: list[str] | None = None, ref_ym: str | None = None,
                 n_retrieve_top: int = 30, include_cv_ids: list[str] | None = None,
                 only_recommendable: bool = False, min_score: int | None = None) -> MatchOutcome:
        """`only_recommendable`, `min_score` (S07): goi y khi co tin moi - chi CV nhan goi y, chi tra diem >= nguong."""
        mx = self.cfg.retrieve.pool_rerank_all_max
        if include_cv_ids is not None and mx is not None and len(set(include_cv_ids)) <= mx:
            n_pool = len(set(include_cv_ids))           # V-20: cham va tra du moi nguoi da nop
            K, N = max(K or 0, n_pool), max(N or 0, n_pool)
        with self.lock.read(), self.connect() as conn:
            with Timer() as t1:
                res = retrieve_for_jd(conn, self.index, self.cfg, jd_id, K=K, hard_filters=self._norm_filters(hard_filters),
                                      exclude_cv_ids=set(exclude_cv_ids or ()), views=views,
                                      include_cv_ids=set(include_cv_ids) if include_cv_ids is not None else None,
                                      only_recommendable=only_recommendable)
            req = res.request if N is None else res.request.model_copy(update={"N": N})
            with Timer() as t2:
                out = self.reranker.rerank(conn, req, ref_ym=ref_ym)
        timings = {"retrieve_s": t1.s, "rerank_s": t2.s, **{f"rerank.{k}": v for k, v in out.timings.items()}}
        items = [{"cv_id": it.cv_id, "rank": it.rank, "score": it.score, "band": band_of(it.score, self.cfg),
                  "cap_applied": it.cap_applied, "flags": list(it.flags), **self._item_extra(it)}
                 for it in out.items if min_score is None or it.score >= min_score]
        top = [{"cv_id": it["cv_id"], "rank": it["rank"], "fused": it["fused"], "s": it["s"]}
               for it in res.items[:n_retrieve_top]]
        log_event("match", run_id=out.run_id, retrieve_run_id=res.run_id, jd_id=jd_id, jd_version=res.jd_version,
                  n_pool=res.n_pool, k=len(res.items), n=len(items), views=res.views_used, **timings)
        return MatchOutcome(out.run_id, res.run_id, jd_id, res.jd_version, res.n_pool, items,
                            res.warnings + out.warnings, timings, top, out.items)

    # ----------------------------------------------------------------- Luong D (CV -> JD)

    def match_cv(self, cv_id: str, *, K: int | None = None, N: int | None = None, hard_filters: dict | None = None,
                 exclude_jd_ids: list[str] | None = None, views: list[str] | None = None,
                 ref_ym: str | None = None, include_jd_ids: list[str] | None = None) -> MatchOutcome:
        with self.lock.read(), self.connect() as conn:
            with Timer() as t1:
                res = retrieve_for_cv(conn, self.jd_index, self.cfg, cv_id, K=K, hard_filters=self._norm_filters(hard_filters),
                                      segmenter=self.ctx.segmenter,
                                      exclude_jd_ids=set(exclude_jd_ids or ()), views=views,
                                      include_jd_ids=set(include_jd_ids) if include_jd_ids is not None else None)
            req = res.request if N is None else res.request.model_copy(update={"N": N})
            with Timer() as t2:
                out = self.reranker.rerank(conn, req, ref_ym=ref_ym)
            # kiem lai jd.status luc tra (JD co the vua dong sau khi tinh, 06 muc 5.5)
            ids = [it.jd_id for it in out.items]
            open_ = {r["jd_id"] for r in conn.execute(
                "SELECT DISTINCT jd_id FROM jd WHERE jd_id = ANY(%s) AND status = 'open'", (ids,))}
        warnings = res.warnings + out.warnings
        closed = [j for j in ids if j not in open_]
        if closed:
            warnings.append({"code": "jd_closed", "message": f"{len(closed)} JD vừa đóng: đã loại khỏi kết quả",
                             "jd_ids": closed})
        final = [it for it in out.items if it.jd_id in open_]
        timings = {"retrieve_s": t1.s, "rerank_s": t2.s, **{f"rerank.{k}": v for k, v in out.timings.items()}}
        items = [{"jd_id": it.jd_id, "jd_version": it.jd_version, "rank": k, "score": it.score,
                  "band": band_of(it.score, self.cfg), "cap_applied": it.cap_applied, "flags": list(it.flags),
                  **self._item_extra(it)}
                 for k, it in enumerate(final, start=1)]
        log_event("match_cv", run_id=out.run_id, retrieve_run_id=res.run_id, cv_id=cv_id, n_pool=res.n_pool,
                  k=len(res.items), n=len(items), fusion=res.fusion, **timings)
        top = [{"jd_id": it["jd_id"], "rank": it["rank"], "fused": it["fused"], "s": it["s"]} for it in res.items]
        return MatchOutcome(out.run_id, res.run_id, cv_id, 0, res.n_pool, items, warnings, timings, top, final)

    def preview_cv(self, raw: dict, *, N: int | None = None, hard_filters: dict | None = None,
                   ref_ym: str | None = None, n_explain: int | None = None) -> dict:
        """CV tam (ung vien tai len xem goi y, 06 muc 5.4): Luong A -> Luong D -> giai thich NGAY, roi XOA HET du
        lieu tam (khong o lai kho, khong vao CvIndex, khong de log match / rerank). CV trung noi dung voi CV da co
        trong kho -> dung CV do (khong xoa)."""
        with self.lock.write():
            tmp = dict(raw)
            tmp["email"] = f"preview-{uuid.uuid4().hex}@preview.local"   # candidate_key rieng: khong de ban that
            tmp["phone"] = None
            self._suppress_index = True
            try:
                with self.connect() as conn:
                    o = CvIngestor(conn, self.ctx, self.encoder).ingest_one(tmp, "preview")
            finally:
                self._suppress_index = False
            temp = o.status == "ok"
            try:
                if o.status not in ("ok", "duplicate"):
                    return {"status": o.status, "detail": o.detail, "items": [], "explanations": [], "warnings": []}
                m = self.match_cv(o.cv_id, N=N, hard_filters=hard_filters, ref_ym=ref_ym)
                k = len(m.items) if n_explain is None else n_explain
                expl = []
                for it in m.items[:k]:
                    e = self.explain(m.run_id, it["jd_id"])
                    expl.append({"jd_id": it["jd_id"], "band": e["band"], "band_label": e["band_label"],
                                 "text": e["text"]})
                return {"status": "ok", "items": m.items, "explanations": expl, "warnings": m.warnings}
            finally:
                if temp:
                    self._purge_preview(o.cv_id)

    def _purge_preview(self, cv_id: str) -> None:
        with self.connect() as conn:
            with conn.transaction():
                texts = [r["text_raw"] for r in conn.execute(
                    "SELECT text_raw FROM cv_bullet WHERE cv_id = %s UNION ALL"
                    " SELECT text_raw FROM cv_summary_sentence WHERE cv_id = %s", (cv_id, cv_id))]
                conn.execute("DELETE FROM match_run WHERE direction = 'cv_to_jd' AND query_id = %s", (cv_id,))
                conn.execute("DELETE FROM ingest_log WHERE entity = 'cv' AND entity_id = %s", (cv_id,))
                conn.execute("DELETE FROM cv WHERE cv_id = %s", (cv_id,))        # cascade moi bang cv_*
        if texts:
            self.scorer.purge_texts(texts)
        log_event("preview_purged", cv_id=cv_id)

    # ----------------------------------------------------------------- Tang 3

    def explain(self, run_id: str, cv_id: str, *, force: bool = False) -> dict:
        with self.lock.read(), self.connect() as conn, Timer() as t:
            out = self.explainer.explain(conn, run_id, cv_id, force=force)
        log_event("explain", run_id=run_id, cv_id=cv_id, duration_s=t.s)
        return out

    # ----------------------------------------------------------------- suc khoe

    def health(self) -> dict:
        v = self.cfg.versions.model_dump()
        try:
            with self.connect() as conn:
                conn.execute("SELECT 1").fetchone()
            db = "ok"
        except Exception as e:  # noqa: BLE001 - health phai tra loi, khong nem
            db = f"error: {type(e).__name__}"
        return {"status": "ok" if db == "ok" else "degraded", "db": db, "versions": v,
                "config_files": dict(self.cfg.files),
                "config_hash": self.cfg.config_hash(), "encoder": self.encoder.key(),
                "n_cv": int(self.index.active.sum()), "n_jd_open": self.jd_index.n_jd,
                "index_memory_mb": self.index.memory_mb(), "warm_cache": self.warm_status,
                "timings": self.timings}
