"""Tang 2 Rerank: RR1-RR4, RR6 (thiet ke 07 muc 4). RR5 (LLM) tat, khong lam.

    RR1 tai theo lo du lieu JD + ~200 CV tu Postgres
    RR2 BERTScore MOT lan cho moi cau JD x moi gach cua ca pool (cache token)
    RR3 feature: A1 (= s_skill o P1), B4 tu R; B1, B2 bang luat. A2, B5, B3, C1: P2 (T15)
    RR4 thieu du lieu -> diem tho -> cong must-have -> 0-100 -> xep hang -> top N
    RR6 ghi rerank_run / rerank_feature / rerank_result + dung FinalItem cho Explain
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import psycopg
from psycopg.types.json import Jsonb

from cvmatch.core.config import AppConfig
from cvmatch.core.contracts import (
    FEATURES, Evidence, ExperienceFacts, FeatureRow, Features, FinalItem, RerankCandidate, RerankRequest,
    SentenceDetail, SentenceFact, ViewScores,
)
from cvmatch.core.db import insert_rows, transaction
from cvmatch.core.kb.rel import RoleDistance, SkillRelations
from cvmatch.core.kb.snapshot import KBSnapshot
from cvmatch.core.models.base import TokenEmb
from cvmatch.rerank.bertscore.align import align_words
from cvmatch.rerank.bertscore.engine import BertScorer
from cvmatch.rerank.features import a1_a2, b4_b5
from cvmatch.rerank.features.b1_b2_b3 import Exp, b1_role, b2_years
from cvmatch.rerank.scoring import Scored, finalize

_MAX_GAP_WORDS = 10


class RerankError(Exception):
    pass


# --------------------------------------------------------------------------- RR1: du lieu


@dataclass
class JdData:
    jd_id: str
    version: int
    resp: list[dict]                 # idx, text_raw, is_generic
    req_items: list[dict]            # idx, text_raw, kind
    skills: list[a1_a2.JdSkill]
    meta: dict


@dataclass
class CvData:
    cv_id: str
    flags: list[str]
    meta: dict
    bullets: list[dict] = field(default_factory=list)   # bullet_id, section, item_idx, pos, text_raw, has_negation, is_coursework
    skills: dict[str, a1_a2.CvSkill] = field(default_factory=dict)
    exps: list[Exp] = field(default_factory=list)


def load_jd(conn: psycopg.Connection, jd_id: str, version: int) -> JdData:
    if conn.execute("SELECT 1 FROM jd WHERE jd_id = %s AND version = %s", (jd_id, version)).fetchone() is None:
        raise RerankError(f"khong co JD {jd_id} v{version}")
    q = lambda sql: conn.execute(sql, (jd_id, version)).fetchall()  # noqa: E731
    resp = q("SELECT idx, text_raw, is_generic FROM jd_responsibility WHERE jd_id=%s AND version=%s ORDER BY idx")
    req = q("SELECT idx, text_raw, kind FROM jd_requirement_item WHERE jd_id=%s AND version=%s ORDER BY idx")
    skills = [a1_a2.JdSkill(r["skill_id"], r["required"], float(r["w_imp"]), r["group_id"]) for r in
              q("SELECT skill_id, required, w_imp, group_id FROM jd_skill WHERE jd_id=%s AND version=%s"
                " ORDER BY required DESC, w_imp DESC, skill_id")]
    meta = conn.execute("SELECT * FROM jd_meta WHERE jd_id=%s AND version=%s", (jd_id, version)).fetchone() or {}
    meta = {k: (float(v) if k in ("min_years", "max_years") and v is not None else v) for k, v in dict(meta).items()}
    return JdData(jd_id, version, [dict(r) for r in resp], [dict(r) for r in req], skills, meta)


def load_cvs(conn: psycopg.Connection, cv_ids: list[str]) -> dict[str, CvData]:
    ids = list(cv_ids)
    out: dict[str, CvData] = {}
    for r in conn.execute("SELECT c.cv_id::text AS cv_id, c.flags, m.location, m.level_rank, m.role_group,"
                          " m.years_experience, m.n_bullets FROM cv c LEFT JOIN cv_meta m USING (cv_id)"
                          " WHERE c.cv_id = ANY(%s::uuid[])", (ids,)):
        meta = {k: r[k] for k in ("location", "level_rank", "role_group", "n_bullets")}
        meta["years_experience"] = float(r["years_experience"]) if r["years_experience"] is not None else None
        out[r["cv_id"]] = CvData(r["cv_id"], list(r["flags"] or []), meta)
    lost = [c for c in ids if c not in out]
    if lost:
        raise RerankError(f"{len(lost)} CV trong request khong con trong DB (vd {lost[0]})")
    for r in conn.execute("SELECT cv_id::text AS cv_id, bullet_id, section, item_idx, pos, text_raw, has_negation,"
                          " is_coursework FROM cv_bullet WHERE cv_id = ANY(%s::uuid[])"
                          " ORDER BY cv_id, section, item_idx, pos", (ids,)):
        out[r["cv_id"]].bullets.append(dict(r))
    for r in conn.execute("SELECT cv_id::text AS cv_id, skill_id, ev, bullet_id, source_field FROM cv_skill"
                          " WHERE cv_id = ANY(%s::uuid[])", (ids,)):
        out[r["cv_id"]].skills[r["skill_id"]] = a1_a2.CvSkill(r["skill_id"], float(r["ev"]), r["bullet_id"],
                                                              r["source_field"])
    for r in conn.execute("SELECT cv_id::text AS cv_id, kind, role_group, start_ym, end_ym, is_current"
                          " FROM cv_experience WHERE cv_id = ANY(%s::uuid[]) ORDER BY cv_id, idx", (ids,)):
        out[r["cv_id"]].exps.append(Exp(r["kind"], r["role_group"], r["start_ym"], r["end_ym"], r["is_current"]))
    return out


def request_from_run(conn: psycopg.Connection, cfg: AppConfig, retrieve_run_id: str, N: int | None = None,
                     ) -> RerankRequest:
    """Dung lai RerankRequest (C8) tu match_run / match_result da ghi."""
    run = conn.execute("SELECT * FROM match_run WHERE run_id = %s", (retrieve_run_id,)).fetchone()
    if run is None:
        raise RerankError(f"khong co retrieve run {retrieve_run_id}")
    if run["direction"] != "jd_to_cv":
        raise RerankError("chieu cv_to_jd lam o T16")
    rows = conn.execute("SELECT * FROM match_result WHERE run_id = %s ORDER BY rank", (retrieve_run_id,)).fetchall()
    views = ("dense", "bm25", "skill", "resp")
    return RerankRequest(
        direction="jd_to_cv", run_id=str(uuid.uuid4()), retrieve_run_id=str(retrieve_run_id), jd_id=run["query_id"],
        jd_version=run["query_version"], N=N or cfg.rerank.N, config_version=cfg.rerank.version,
        bertscore_config=cfg.bertscore.key(),
        candidates=[RerankCandidate(cv_id=r["item_id"], rank=r["rank"],
                                    s=ViewScores(**{v: r[f"s_{v}"] for v in views}),
                                    n=ViewScores(**{v: r[f"n_{v}"] for v in views}), fused=r["fused"])
                    for r in rows])


# --------------------------------------------------------------------------- ket qua


@dataclass
class RerankOutput:
    run_id: str
    items: list[FinalItem]            # top N
    rows: list[FeatureRow]            # moi CV trong pool, theo hang
    timings: dict[str, float]
    warnings: list[dict] = field(default_factory=list)


def _bullet_flags(b: dict) -> list[str]:
    return [f for f in ("has_negation", "is_coursework") if b.get(f)]


class Reranker:
    def __init__(self, cfg: AppConfig, scorer: BertScorer, snapshot: KBSnapshot):
        if scorer.cfg.key() != cfg.bertscore.key():
            raise ValueError("BertScorer khac bertscore_config cua config")
        self.cfg = cfg
        self.rc = cfg.rerank
        self.scorer = scorer
        self.snapshot = snapshot
        self.M = RoleDistance(snapshot)
        self.rels = SkillRelations.from_config(snapshot, self.rc.rel)
        from cvmatch.core.text.segment import make_segmenter

        self.segmenter = make_segmenter(cfg.prep.segmenter, cfg.prep.protected_tokens)   # gop am tiet -> tu

    # ----------------------------------------------------------------- RR2

    def _bertscore(self, jd_texts: list[str], cvs: list[CvData]):
        sc = self.scorer
        jd_prep = sc.prepare(jd_texts)
        jd_emb = sc.embed(jd_prep)
        bullets = [b for c in cvs for b in c.bullets]
        cv_prep = sc.prepare([b["text_raw"] for b in bullets])
        cv_emb = sc.embed(cv_prep)
        R = sc.score_embs(jd_emb, cv_emb)
        return jd_prep, jd_emb, cv_prep, cv_emb, R

    # ----------------------------------------------------------------- B4

    def _b4(self, jd: JdData, cvs: list[CvData], timings: dict):
        b4 = self.rc.b4
        sents = [r for r in jd.resp if not r["is_generic"] or b4.generic_weight > 0]
        w = b4_b5.sentence_weights([r["is_generic"] for r in sents], b4.generic_weight)
        res: dict[str, tuple[float | None, str | None, list[SentenceDetail]]] = {}
        if b4_b5.aggregate(np.zeros(len(w), np.float32), w) is None:
            return {c.cv_id: (None, "jd_side", []) for c in cvs}
        scorable = [c for c in cvs if c.bullets and "no_diacritics" not in c.flags]
        t = time.perf_counter()
        jd_prep, jd_emb, cv_prep, cv_emb, R = self._bertscore([s["text_raw"] for s in sents], scorable)
        timings["rr2_bertscore_s"] = round(time.perf_counter() - t, 4)
        t = time.perf_counter()
        dim = jd_emb[0].emb.shape[1] if jd_emb else 1024
        empty = TokenEmb(tokens=[], offsets=[], emb=np.zeros((0, dim), np.float32))
        scorable_ids = {c.cv_id for c in scorable}
        col = 0
        for c in cvs:
            if c.cv_id not in scorable_ids:
                res[c.cv_id] = (None, "cv_side", [])
                continue
            n = len(c.bullets)
            Rc = R[:, col:col + n]
            embs = cv_emb[col:col + n]
            preps = cv_prep[col:col + n]
            col += n
            m = b4_b5.bullet_multipliers(np.array([b["has_negation"] for b in c.bullets]),
                                         np.array([b["is_coursework"] for b in c.bullets]), b4)
            ss = b4_b5.sentence_scores(Rc, m, b4)
            details = []
            for j, s in enumerate(sents):
                bi = int(ss.best[j])
                bullet = c.bullets[bi] if bi >= 0 else None
                matched, missing, _ = align_words(
                    jd_prep[j], jd_emb[j], embs[bi] if bullet else empty, self.rc.align.word_sim_min, self.segmenter,
                    cv_text=preps[bi].text if bullet and self.rc.align.literal_match else None)
                details.append(SentenceDetail(
                    resp_idx=s["idx"], c_j=round(float(ss.c[j]), 6), R_best=round(float(ss.R_best[j]), 6),
                    bullet_id=bullet["bullet_id"] if bullet else None, level=b4_b5.level_of(float(ss.c[j]), b4),
                    matched_words=matched if bullet else [], missing_words=missing,
                    bullet_flags=_bullet_flags(bullet) if bullet else []))
            res[c.cv_id] = (b4_b5.aggregate(ss.c, w), None, details)
        timings["rr3_b4_align_s"] = round(time.perf_counter() - t, 4)
        return res

    # ----------------------------------------------------------------- RR1-RR6

    def rerank(self, conn: psycopg.Connection, request: RerankRequest, *, ref_ym: str | None = None,
               write: bool = True) -> RerankOutput:
        if request.direction != "jd_to_cv":
            raise RerankError("chieu cv_to_jd lam o T16")
        if request.bertscore_config != self.cfg.bertscore.key():
            raise RerankError(f"request bertscore_config {request.bertscore_config} khac config hien tai")
        ref_ym = ref_ym or date.today().strftime("%Y-%m")
        rc = self.rc
        timings: dict[str, float] = {}
        t0 = time.perf_counter()
        jd = load_jd(conn, request.jd_id, request.jd_version)                                  # RR1
        cand = {c.cv_id: c for c in request.candidates}
        cv_map = load_cvs(conn, list(cand))
        cvs = [cv_map[c.cv_id] for c in request.candidates]
        timings["rr1_load_s"] = round(time.perf_counter() - t0, 4)

        on = set(rc.features_enabled)
        b4 = self._b4(jd, cvs, timings) if "B4" in on else {}                                 # RR2 + B4
        has_req = any(s.required for s in jd.skills)
        g_jd = jd.meta.get("role_group")
        warnings: list[dict] = []
        for f in sorted(on - {"A1", "B4", "B1", "B2"}):
            warnings.append({"code": "feature_not_implemented", "message": f"{f} chua lam (T15): bo qua"})

        t = time.perf_counter()
        scored: list[Scored] = []
        extra: dict[str, dict] = {}
        for c in cvs:                                                                         # RR3
            raw = {f: None for f in FEATURES}
            missing: dict[str, str] = {}
            if "A1" in on:
                if not has_req:
                    missing["A1"] = "jd_side"
                elif rc.a1.use_kb_rel:
                    raw["A1"] = a1_a2.coverage(jd.skills, c.skills, True, self.rels.rel)
                else:
                    s = cand[c.cv_id].s.skill
                    raw["A1"] = float(s) if s is not None else a1_a2.coverage(jd.skills, c.skills, True)
            if "B4" in on:
                raw["B4"], side, details = b4[c.cv_id]
                if side:
                    missing["B4"] = side
            else:
                details = []
            if "B1" in on:
                raw["B1"], side, _ = b1_role(c.exps, g_jd, self.M, rc.b1, rc.b2, ref_ym)
                if side:
                    missing["B1"] = side
            y = None
            if "B2" in on:
                raw["B2"], side, y = b2_years(c.exps, g_jd, self.M, rc.b2, jd.meta.get("min_years"),
                                              jd.meta.get("max_years"))
                if side:
                    missing["B2"] = side
            flags = []
            if "no_diacritics" in c.flags:
                flags.append("no_diacritics")
            if any(b["has_negation"] for b in c.bullets):
                flags.append("has_negation_bullets")
            if any(b["is_coursework"] for b in c.bullets):
                flags.append("has_coursework_bullets")
            loc_jd, loc_cv = jd.meta.get("location"), c.meta.get("location")
            if loc_jd and loc_cv and loc_jd != loc_cv and jd.meta.get("work_mode") != "remote":
                flags.append("location_mismatch")
            if any(r["kind"] == "language" for r in jd.req_items):
                flags.append("check_language")
            # lam tron 6 chu so: s_skill doc tu cot `real` (float32) hay tu RAM phai cho cung ket qua
            raw = {f: (round(float(v), 6) if v is not None else None) for f, v in raw.items()}
            scored.append(Scored(c.cv_id, raw, missing, flags=flags))
            extra[c.cv_id] = {"resp_detail": details, "relevant_years": y}
        timings["rr3_rules_s"] = round(time.perf_counter() - t, 4)

        ordered = finalize(scored, rc)                                                        # RR4
        rows = [FeatureRow(cv_id=r.item_id, features=Features(**r.used), missing=r.missing,
                           resp_detail=extra[r.item_id]["resp_detail"], s_raw=round(r.s_raw, 6),
                           gate_cap=r.gate_cap, score=r.score, flags=r.flags) for r in ordered]
        top = ordered[: request.N]
        items = [self._final_item(r, jd, cv_map[r.item_id], extra[r.item_id]) for r in top]   # RR6
        timings["total_s"] = round(time.perf_counter() - t0, 4)
        if write:
            years = {k: v["relevant_years"] for k, v in extra.items()}
            self._write(conn, request, ordered, rows, items, timings, ref_ym, years)
        return RerankOutput(request.run_id, items, rows, timings, warnings)

    # ----------------------------------------------------------------- RR6

    def _name(self, sid: str) -> str:
        s = self.snapshot.skills.get(sid)
        return s.name if s else sid

    def _final_item(self, r: Scored, jd: JdData, c: CvData, ex: dict) -> FinalItem:
        facts = a1_a2.skill_facts(jd.skills, c.skills, self.rels.relation)
        resp_text = {s["idx"]: s["text_raw"] for s in jd.resp}
        bullets = {b["bullet_id"]: b for b in c.bullets}
        resp_facts = [SentenceFact(resp_id=d.resp_idx, resp_text=resp_text[d.resp_idx], level=d.level,
                                   evidence_id=str(d.bullet_id) if d.bullet_id is not None else None,
                                   matched_words=d.matched_words, missing_words=d.missing_words)
                      for d in ex["resp_detail"]]
        evidence: dict[str, Evidence] = {}
        ev_ids = [f.evidence_id for f in resp_facts if f.evidence_id] + [m.evidence_id for m in facts.met]
        for eid in ev_ids:
            if eid.isdigit() and int(eid) in bullets:
                b = bullets[int(eid)]
                evidence[eid] = Evidence(text_raw=b["text_raw"], section=b["section"], item_idx=b["item_idx"],
                                         flags=_bullet_flags(b))
        gaps = [self._name(s) for s in facts.missing]
        gaps += [f.resp_text for f in resp_facts if f.level == "not_evidenced"]
        words = []
        for f in resp_facts:
            if f.level == "partial":
                words += [w for w in f.missing_words if w not in words]
        gaps += words[:_MAX_GAP_WORDS]
        exp = ExperienceFacts(relevant_years=round(ex["relevant_years"], 1) if ex["relevant_years"] is not None else None,
                              level_cv=c.meta.get("level_rank"), level_jd=jd.meta.get("level_rank"),
                              role_group_cv=c.meta.get("role_group"), role_group_jd=jd.meta.get("role_group"))
        return FinalItem(cv_id=c.cv_id, rank=r.rank, score=r.score, score_raw=round(r.s_raw, 6), gate_cap=r.gate_cap,
                         cap_applied=r.cap_applied, features=Features(**r.used), missing=r.missing,
                         skill_facts=facts, resp_facts=resp_facts, experience_facts=exp, gaps=gaps,
                         evidence=evidence, flags=list(r.flags))

    def _write(self, conn, request: RerankRequest, ordered: list[Scored], rows: list[FeatureRow],
               items: list[FinalItem], timings: dict, ref_ym: str, extra_years: dict) -> None:
        cfg_json = {"rerank": self.rc.model_dump(mode="json"), "ref_ym": ref_ym, "jd_id": request.jd_id,
                    "jd_version": request.jd_version, "ontology_version": self.snapshot.ontology_version}
        by_id = {r.item_id: r for r in ordered}
        with transaction(conn) as cur:
            cur.execute("INSERT INTO rerank_run(run_id, retrieve_run_id, direction, n, config_json, config_hash,"
                        " bertscore_config, rerank_config_version, timings_json)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (request.run_id, request.retrieve_run_id, request.direction, request.N, Jsonb(cfg_json),
                         self.cfg.config_hash(), request.bertscore_config, self.rc.version, Jsonb(timings)))
            insert_rows(cur, "rerank_feature",
                        ("run_id", "item_id", "features_json", "missing_json", "detail_json", "s_raw", "gate_cap"),
                        [(request.run_id, f.cv_id, Jsonb(f.features.model_dump()), Jsonb(f.missing),
                          Jsonb({"resp_detail": [d.model_dump() for d in f.resp_detail],
                                 "req_detail": [d.model_dump() for d in f.req_detail],
                                 "raw": by_id[f.cv_id].raw, "flags": f.flags, "rank": by_id[f.cv_id].rank,
                                 "score": f.score, "relevant_years": extra_years.get(f.cv_id)}),
                          f.s_raw, f.gate_cap) for f in rows])
            insert_rows(cur, "rerank_result",
                        ("run_id", "item_id", "rank", "score", "score_raw", "cap_applied", "facts_json"),
                        [(request.run_id, it.cv_id, it.rank, it.score, it.score_raw, it.cap_applied,
                          Jsonb(it.model_dump(mode="json"))) for it in items])
