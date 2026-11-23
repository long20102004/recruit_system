"""Tang 2 Rerank: RR1-RR4, RR6 (thiet ke 07 muc 4, 8). RR5 (LLM) tat, khong lam.

    RR1 tai theo lo du lieu JD + CV tu Postgres
    RR2 BERTScore MOT lan cho moi cau JD x moi ung vien phia CV cua ca pool (cache token)
    RR3 feature: A1, A2 (qua KB khi a1.use_kb_rel), B4, B5 tu R; B1, B2, B3, C1 bang luat
    RR4 thieu du lieu -> diem tho -> cong must-have -> 0-100 -> xep hang -> top N
    RR6 ghi rerank_run / rerank_feature / rerank_result + dung FinalItem cho Explain

Hai chieu dung chung code (07 muc 8): `jd_to_cv` (mot JD, ~200 CV) va `cv_to_jd` (mot CV, <= 60 JD).
Cau JD luon la tham chieu, ung vien phia CV la gach (B4) hoac gach + cau summary (B5).
Chieu nguoc: mau so A1/A2 >= `reverse.skill.min_imp_sum`, tat phat thua B2/B3.
"""

from __future__ import annotations

import logging
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
from cvmatch.core.text.normalize import normalize
from cvmatch.core.text.patterns import PatternList, read_pattern_file
from cvmatch.rerank.bertscore.align import align_words
from cvmatch.rerank.bertscore.engine import BertScorer
from cvmatch.rerank.features import a1_a2, b4_b5
from cvmatch.rerank.features.b1_b2_b3 import Exp, b1_role, b2_years, b3_level, cv_level, spearman
from cvmatch.rerank.features.c1 import Edu, c1_education
from cvmatch.rerank.scoring import Scored, finalize

log = logging.getLogger(__name__)
_MAX_GAP_WORDS = 10
IMPLEMENTED = {"A1", "A2", "B4", "B5", "B1", "B2", "B3", "C1"}


class RerankError(Exception):
    pass


# --------------------------------------------------------------------------- RR1: du lieu


@dataclass
class JdData:
    jd_id: str
    version: int
    resp: list[dict]                 # idx, text_raw, is_generic (+ dense khi can cosine)
    req_items: list[dict]            # idx, text_raw, kind
    skills: list[a1_a2.JdSkill]
    meta: dict
    status: str = "open"
    unmapped_required: list[str] = field(default_factory=list)   # ky nang bat buoc khong co trong KB

    @property
    def key(self) -> str:
        return f"{self.jd_id}@{self.version}"


@dataclass
class CvData:
    cv_id: str
    flags: list[str]
    meta: dict
    bullets: list[dict] = field(default_factory=list)   # bullet_id, section, item_idx, pos, text_raw, has_negation, is_coursework
    summary: list[dict] = field(default_factory=list)   # idx, text_raw, has_negation, is_coursework
    skills: dict[str, a1_a2.CvSkill] = field(default_factory=dict)
    exps: list[Exp] = field(default_factory=list)
    edus: list[Edu] = field(default_factory=list)


def _unmapped_required(raw_json: dict, mapped_raw: set[str]) -> list[str]:
    out = []
    for s in (raw_json or {}).get("skills") or []:
        name = s.get("name") if isinstance(s, dict) else s
        required = s.get("required", True) if isinstance(s, dict) else True
        if name and required and name not in mapped_raw:
            out.append(str(name))
    return out


def load_jd(conn: psycopg.Connection, jd_id: str, version: int, *, with_dense: bool = False) -> JdData:
    head = conn.execute("SELECT status, raw_json FROM jd WHERE jd_id = %s AND version = %s", (jd_id, version)).fetchone()
    if head is None:
        raise RerankError(f"khong co JD {jd_id} v{version}")
    q = lambda sql: conn.execute(sql, (jd_id, version)).fetchall()  # noqa: E731
    if with_dense:
        with conn.cursor(binary=True) as cur:
            cur.execute("SELECT idx, text_raw, is_generic, dense FROM jd_responsibility WHERE jd_id=%s AND version=%s"
                        " ORDER BY idx", (jd_id, version))
            resp = [{**r, "dense": r["dense"].to_numpy().astype(np.float32) if r["dense"] is not None else None}
                    for r in cur.fetchall()]
    else:
        resp = q("SELECT idx, text_raw, is_generic FROM jd_responsibility WHERE jd_id=%s AND version=%s ORDER BY idx")
    req = q("SELECT idx, text_raw, kind FROM jd_requirement_item WHERE jd_id=%s AND version=%s ORDER BY idx")
    srows = q("SELECT skill_id, required, w_imp, group_id, source, raw_text FROM jd_skill WHERE jd_id=%s AND version=%s"
              " ORDER BY required DESC, w_imp DESC, skill_id")
    skills = [a1_a2.JdSkill(r["skill_id"], r["required"], float(r["w_imp"]), r["group_id"]) for r in srows]
    meta = conn.execute("SELECT * FROM jd_meta WHERE jd_id=%s AND version=%s", (jd_id, version)).fetchone() or {}
    meta = {k: (float(v) if k in ("min_years", "max_years") and v is not None else v) for k, v in dict(meta).items()}
    unmapped = _unmapped_required(head["raw_json"], {r["raw_text"] for r in srows if r["source"] == "module1"})
    return JdData(jd_id, version, [dict(r) for r in resp], [dict(r) for r in req], skills, meta, head["status"],
                  unmapped)


def load_cvs(conn: psycopg.Connection, cv_ids: list[str], *, with_dense: bool = False) -> dict[str, CvData]:
    ids = list(cv_ids)
    out: dict[str, CvData] = {}
    for r in conn.execute("SELECT c.cv_id::text AS cv_id, c.flags, m.location, m.level_rank, m.level_source,"
                          " m.role_group, m.years_experience, m.n_bullets FROM cv c LEFT JOIN cv_meta m USING (cv_id)"
                          " WHERE c.cv_id = ANY(%s::uuid[])", (ids,)):
        meta = {k: r[k] for k in ("location", "level_rank", "level_source", "role_group", "n_bullets")}
        meta["years_experience"] = float(r["years_experience"]) if r["years_experience"] is not None else None
        out[r["cv_id"]] = CvData(r["cv_id"], list(r["flags"] or []), meta)
    lost = [c for c in ids if c not in out]
    if lost:
        raise RerankError(f"{len(lost)} CV trong request khong con trong DB (vd {lost[0]})")
    with conn.cursor(binary=with_dense) as cur:
        cur.execute("SELECT b.cv_id::text AS cv_id, b.bullet_id, b.section, b.item_idx, b.pos, b.text_raw,"
                    " b.has_negation, b.is_coursework" + (", v.dense" if with_dense else "") +
                    " FROM cv_bullet b" + (" LEFT JOIN cv_bullet_vector v USING (bullet_id)" if with_dense else "") +
                    " WHERE b.cv_id = ANY(%s::uuid[]) ORDER BY b.cv_id, b.section, b.item_idx, b.pos", (ids,))
        for r in cur.fetchall():
            d = dict(r)
            if with_dense:
                d["dense"] = r["dense"].to_numpy().astype(np.float32) if r["dense"] is not None else None
            out[r["cv_id"]].bullets.append(d)
    for r in conn.execute("SELECT cv_id::text AS cv_id, idx, text_raw, has_negation, is_coursework"
                          " FROM cv_summary_sentence WHERE cv_id = ANY(%s::uuid[]) ORDER BY cv_id, idx", (ids,)):
        out[r["cv_id"]].summary.append(dict(r))
    for r in conn.execute("SELECT cv_id::text AS cv_id, skill_id, ev, bullet_id, source_field FROM cv_skill"
                          " WHERE cv_id = ANY(%s::uuid[])", (ids,)):
        out[r["cv_id"]].skills[r["skill_id"]] = a1_a2.CvSkill(r["skill_id"], float(r["ev"]), r["bullet_id"],
                                                              r["source_field"])
    for r in conn.execute("SELECT cv_id::text AS cv_id, kind, role_group, start_ym, end_ym, is_current"
                          " FROM cv_experience WHERE cv_id = ANY(%s::uuid[]) ORDER BY cv_id, idx", (ids,)):
        out[r["cv_id"]].exps.append(Exp(r["kind"], r["role_group"], r["start_ym"], r["end_ym"], r["is_current"]))
    for r in conn.execute("SELECT cv_id::text AS cv_id, major_group, status, expected_end_ym FROM cv_education"
                          " WHERE cv_id = ANY(%s::uuid[]) ORDER BY cv_id, idx", (ids,)):
        out[r["cv_id"]].edus.append(Edu(r["major_group"], r["status"], r["expected_end_ym"]))
    return out


def request_from_run(conn: psycopg.Connection, cfg: AppConfig, retrieve_run_id: str, N: int | None = None,
                     ) -> RerankRequest:
    """Dung lai RerankRequest (C8 / D8) tu match_run / match_result da ghi."""
    run = conn.execute("SELECT * FROM match_run WHERE run_id = %s", (retrieve_run_id,)).fetchone()
    if run is None:
        raise RerankError(f"khong co retrieve run {retrieve_run_id}")
    rows = conn.execute("SELECT * FROM match_result WHERE run_id = %s ORDER BY rank", (retrieve_run_id,)).fetchall()
    views = ("dense", "bm25", "skill", "resp")
    cands = []
    for r in rows:
        ver = (r["explanation_json"] or {}).get("jd_version") if run["direction"] == "cv_to_jd" else None
        cands.append(RerankCandidate(cv_id=r["item_id"], version=ver, rank=r["rank"],
                                     s=ViewScores(**{v: r[f"s_{v}"] for v in views}),
                                     n=ViewScores(**{v: r[f"n_{v}"] for v in views}), fused=r["fused"]))
    common = dict(run_id=str(uuid.uuid4()), retrieve_run_id=str(retrieve_run_id), config_version=cfg.rerank.version,
                  bertscore_config=cfg.bertscore.key(), candidates=cands)
    if run["direction"] == "jd_to_cv":
        return RerankRequest(direction="jd_to_cv", jd_id=run["query_id"], jd_version=run["query_version"],
                             N=N or cfg.rerank.N, **common)
    return RerankRequest(direction="cv_to_jd", cv_id=run["query_id"], N=N or cfg.rerank.reverse_N, **common)


# --------------------------------------------------------------------------- ket qua


@dataclass
class RerankOutput:
    run_id: str
    items: list[FinalItem]            # top N
    rows: list[FeatureRow]            # moi muc trong pool, theo hang (cv_to_jd: FeatureRow.cv_id = jd_id)
    timings: dict[str, float]
    warnings: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def _bullet_flags(b: dict) -> list[str]:
    return [f for f in ("has_negation", "is_coursework") if b.get(f)]


@dataclass
class _Cand:
    """Mot ung vien phia CV cho cau JD: gach (B4, B5) hoac cau summary (B5)."""

    evidence_id: str
    bullet_id: int | None
    text_raw: str
    has_negation: bool
    is_coursework: bool
    section: str
    item_idx: int
    dense: np.ndarray | None = None


def _cands(c: CvData, with_summary: bool) -> list[_Cand]:
    out = [_Cand(str(b["bullet_id"]), b["bullet_id"], b["text_raw"], b["has_negation"], b["is_coursework"],
                 b["section"], b["item_idx"], b.get("dense")) for b in c.bullets]
    if with_summary:
        out += [_Cand(f"summary[{s['idx']}]", None, s["text_raw"], s["has_negation"], s["is_coursework"], "summary",
                      0) for s in c.summary]
    return out


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
        path = cfg.config_dir / self.rc.b3.scope_patterns
        self.scope = PatternList(read_pattern_file(path)) if path.exists() else PatternList([])

    # ----------------------------------------------------------------- RR2 + B4 / B5

    def _sentence_feature(self, kind: str, jds: list[JdData], cvs: list[CvData], timings: dict,
                          ) -> dict[tuple[str, str], tuple[float | None, str | None, list[SentenceDetail]]]:
        """B4 (trach nhiem x gach) hoac B5 (yeu cau dang chu x gach + summary) cho moi cap (JD, CV).

        BERTScore tinh MOT lan cho toan bo cau JD x toan bo ung vien phia CV (moi cau embed mot lan, co cache).
        """
        b4 = self.rc.b4
        engine = b4.engine if kind == "B4" else "bertscore"
        sents: dict[str, list[dict]] = {}
        weights: dict[str, np.ndarray] = {}
        for jd in jds:
            if kind == "B4":
                s = [r for r in jd.resp if not r["is_generic"] or b4.generic_weight > 0]
                w = b4_b5.sentence_weights([r["is_generic"] for r in s], b4.generic_weight)
            else:
                s = [r for r in jd.req_items if r["kind"] == "text"]
                w = np.ones(len(s), np.float32)
            sents[jd.key], weights[jd.key] = s, w
        cands = {c.cv_id: _cands(c, kind == "B5" and self.rc.b5.use_summary) for c in cvs}
        scorable = [c for c in cvs if cands[c.cv_id] and "no_diacritics" not in c.flags]

        res: dict = {}
        jd_ok = [jd for jd in jds if b4_b5.aggregate(np.zeros(len(weights[jd.key]), np.float32), weights[jd.key])
                 is not None]
        ok_keys = {jd.key for jd in jd_ok}
        for jd in jds:
            if jd.key not in ok_keys:
                for c in cvs:
                    res[(jd.key, c.cv_id)] = (None, "jd_side", [])
        if not jd_ok:
            return res

        t = time.perf_counter()
        jd_rows = [(jd, s) for jd in jd_ok for s in sents[jd.key]]
        cv_rows = [(c, x) for c in scorable for x in cands[c.cv_id]]
        R = np.zeros((len(jd_rows), len(cv_rows)), np.float32)
        jd_prep = jd_emb = cv_prep = cv_emb = None
        if engine != "cosine" and jd_rows and cv_rows:
            sc = self.scorer
            jd_prep = sc.prepare([s["text_raw"] for _, s in jd_rows])
            jd_emb = sc.embed(jd_prep)
            cv_prep = sc.prepare([x.text_raw for _, x in cv_rows])
            cv_emb = sc.embed(cv_prep)
            R = sc.score_embs(jd_emb, cv_emb)
        cos = None
        if engine != "bertscore" and jd_rows and cv_rows:
            dim = next((x.dense.shape[0] for _, x in cv_rows if x.dense is not None), 1024)
            Q = np.stack([s.get("dense") if s.get("dense") is not None else np.zeros(dim, np.float32) for _, s in jd_rows])
            C = np.stack([x.dense if x.dense is not None else np.zeros(dim, np.float32) for _, x in cv_rows])
            cos = Q @ C.T
        timings[f"rr2_{kind.lower()}_bertscore_s"] = round(time.perf_counter() - t, 4)

        t = time.perf_counter()
        row_of = {}
        r0 = 0
        for jd in jd_ok:
            n = len(sents[jd.key])
            row_of[jd.key] = (r0, r0 + n)
            r0 += n
        col_of = {}
        c0 = 0
        for c in scorable:
            n = len(cands[c.cv_id])
            col_of[c.cv_id] = (c0, c0 + n)
            c0 += n
        empty = TokenEmb(tokens=[], offsets=[], emb=np.zeros((0, 1024), np.float32))
        for jd in jd_ok:
            ra, rb = row_of[jd.key]
            for c in cvs:
                if c.cv_id not in col_of:
                    res[(jd.key, c.cv_id)] = (None, "cv_side", [])
                    continue
                ca, cb = col_of[c.cv_id]
                cl = cands[c.cv_id]
                Rc = R[ra:rb, ca:cb]
                m = b4_b5.bullet_multipliers(np.array([x.has_negation for x in cl]),
                                             np.array([x.is_coursework for x in cl]), b4)
                cal = b4_b5.calibrated(Rc, b4, cos[ra:rb, ca:cb] if cos is not None else None)
                ss = b4_b5.sentence_scores(Rc, m, b4, cal_base=cal)
                details = []
                for j, s in enumerate(sents[jd.key]):
                    bi = int(ss.best[j])
                    x = cl[bi] if bi >= 0 else None
                    matched, missing = [], []
                    if jd_emb is not None:
                        jj = ra + j
                        matched, missing, _ = align_words(
                            jd_prep[jj], jd_emb[jj], cv_emb[ca + bi] if x else empty, self.rc.align.word_sim_min,
                            self.segmenter,
                            cv_text=cv_prep[ca + bi].text if x and self.rc.align.literal_match else None)
                    details.append(SentenceDetail(
                        resp_idx=s["idx"], c_j=round(float(ss.c[j]), 6), R_best=round(float(ss.R_best[j]), 6),
                        bullet_id=x.bullet_id if x else None, evidence_id=x.evidence_id if x else None,
                        level=b4_b5.level_of(float(ss.c[j]), b4), matched_words=matched if x else [],
                        missing_words=missing,
                        bullet_flags=[f for f, v in (("has_negation", x.has_negation),
                                                     ("is_coursework", x.is_coursework)) if v] if x else []))
                res[(jd.key, c.cv_id)] = (b4_b5.aggregate(ss.c, weights[jd.key]), None, details)
        timings[f"rr3_{kind.lower()}_align_s"] = round(time.perf_counter() - t, 4)
        return res

    # ----------------------------------------------------------------- RR3 cho mot cap

    def _rules(self, jd: JdData, c: CvData, cand: RerankCandidate, reverse: bool, ref_ym: str,
               sent: dict[str, tuple], on: set[str]) -> tuple[Scored, dict]:
        rc = self.rc
        raw = {f: None for f in FEATURES}
        missing: dict[str, str] = {}
        min_den = self.cfg.retrieve.reverse.skill.min_imp_sum if reverse else 0.0
        rel = self.rels.rel if rc.a1.use_kb_rel else None
        if "A1" in on:
            if not any(s.required for s in jd.skills):
                missing["A1"] = "jd_side"
            elif rc.a1.use_kb_rel:
                raw["A1"] = a1_a2.coverage(jd.skills, c.skills, True, rel, min_den=min_den)
            else:
                s = cand.s.skill
                raw["A1"] = float(s) if s is not None else a1_a2.coverage(jd.skills, c.skills, True, min_den=min_den)
        if "A2" in on:
            raw["A2"] = a1_a2.coverage(jd.skills, c.skills, False, rel, min_den=min_den)
            if raw["A2"] is None:
                missing["A2"] = "jd_side"
        details: dict[str, list] = {"B4": [], "B5": []}
        for f in ("B4", "B5"):
            if f in on:
                raw[f], side, details[f] = sent[f][(jd.key, c.cv_id)]
                if side:
                    missing[f] = side
        g_jd = jd.meta.get("role_group")
        if "B1" in on:
            raw["B1"], side, _ = b1_role(c.exps, g_jd, self.M, rc.b1, rc.b2, ref_ym)
            if side:
                missing["B1"] = side
        pen_b2 = rc.b2.overqual_penalty_reverse if reverse else rc.b2.overqual_penalty
        b2_val, b2_side, y = b2_years(c.exps, g_jd, self.M, rc.b2, jd.meta.get("min_years"), jd.meta.get("max_years"),
                                      overqual_penalty=pen_b2)
        if "B2" in on:
            raw["B2"] = b2_val
            if b2_side:
                missing["B2"] = b2_side
        y_any = y
        level_cv, level_src = None, None
        if "B3" in on:
            texts = [normalize(b["text_raw"]) for b in c.bullets]
            scope = any(t in self.scope for t in texts)
            studying = any(e.status == "studying" for e in c.edus) and not any(e.status == "graduated" for e in c.edus)
            level_cv, level_src = cv_level(c.meta.get("level_rank"), c.meta.get("level_source"), scope, y_any,
                                           studying, self.cfg.prep.level_from_years, rc.b3)
            pen_b3 = rc.b3.overqual_penalty_reverse if reverse else True
            raw["B3"], side = b3_level(level_cv, jd.meta.get("level_rank"), rc.b3, overqual_penalty=pen_b3)
            if side:
                missing["B3"] = side
        c1_val = None
        if "C1" in on:
            c1_val, side = c1_education(c.edus, jd.meta.get("edu_required"), ref_ym, rc.c1)
            raw["C1"] = c1_val
            if side:
                missing["C1"] = side
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
        if jd.unmapped_required and ("A1" in on):
            flags.append("unmapped_req")
        # lam tron 6 chu so: s_skill doc tu cot `real` (float32) hay tu RAM phai cho cung ket qua
        raw = {f: (round(float(v), 6) if v is not None else None) for f, v in raw.items()}
        item_id = jd.jd_id if reverse else c.cv_id
        # Chieu nguoc: min_imp_sum chi de XEP HANG giua cac JD (06 muc 5.5c). Cong must-have xet CV co du ky nang
        # bat buoc CUA JD NAY hay khong -> dung do phu khong mau so toi thieu (khong thi CV du ky nang van bi tran 50).
        gate_a1 = None
        if reverse and "A1" in on and "A1" not in missing:
            gate_a1 = a1_a2.coverage(jd.skills, c.skills, True, rel)
        extra = {"resp_detail": details["B4"], "req_detail": details["B5"], "relevant_years": y_any,
                 "level_cv": level_cv, "level_source": level_src, "edu_fit": c1_val}
        return Scored(item_id, raw, missing, flags=flags, gate_a1=gate_a1), extra

    # ----------------------------------------------------------------- RR1-RR6

    def rerank(self, conn: psycopg.Connection, request: RerankRequest, *, ref_ym: str | None = None,
               write: bool = True) -> RerankOutput:
        if request.bertscore_config != self.cfg.bertscore.key():
            raise RerankError(f"request bertscore_config {request.bertscore_config} khac config hien tai")
        reverse = request.direction == "cv_to_jd"
        ref_ym = ref_ym or date.today().strftime("%Y-%m")
        rc = self.rc
        timings: dict[str, float] = {}
        t0 = time.perf_counter()
        dense = rc.b4.engine != "bertscore"
        if reverse:                                                                         # RR1
            cv_map = load_cvs(conn, [request.cv_id], with_dense=dense)
            cv = cv_map[request.cv_id]
            jds = []
            for cnd in request.candidates:
                ver = cnd.version or conn.execute("SELECT version FROM jd WHERE jd_id = %s AND is_latest",
                                                  (cnd.cv_id,)).fetchone()["version"]
                jds.append(load_jd(conn, cnd.cv_id, ver, with_dense=dense))
            pairs = [(jd, cv, cnd) for jd, cnd in zip(jds, request.candidates)]
            cvs = [cv]
        else:
            jd = load_jd(conn, request.jd_id, request.jd_version, with_dense=dense)
            cv_map = load_cvs(conn, [c.cv_id for c in request.candidates], with_dense=dense)
            cvs = [cv_map[c.cv_id] for c in request.candidates]
            jds = [jd]
            pairs = [(jd, c, cnd) for c, cnd in zip(cvs, request.candidates)]
        timings["rr1_load_s"] = round(time.perf_counter() - t0, 4)

        on = set(rc.features_enabled)
        warnings: list[dict] = []
        for f in sorted(on - IMPLEMENTED):
            warnings.append({"code": "feature_not_implemented", "message": f"{f} chua lam: bo qua"})
        sent = {f: (self._sentence_feature(f, jds, cvs, timings) if f in on else {}) for f in ("B4", "B5")}

        t = time.perf_counter()
        scored: list[Scored] = []
        extra: dict[str, dict] = {}
        ctx: dict[str, tuple[JdData, CvData]] = {}
        for jd, c, cnd in pairs:                                                            # RR3
            s, ex = self._rules(jd, c, cnd, reverse, ref_ym, sent, on)
            scored.append(s)
            extra[s.item_id] = ex
            ctx[s.item_id] = (jd, c)
        timings["rr3_rules_s"] = round(time.perf_counter() - t, 4)

        stats: dict = {}
        if "B2" in on and "B3" in on:
            pts = [(s.raw["B2"], s.raw["B3"]) for s in scored if s.raw["B2"] is not None and s.raw["B3"] is not None]
            rho = spearman([p[0] for p in pts], [p[1] for p in pts])
            stats["rho_b2_b3"] = rho
            if rho is not None and rho > rc.b3.rho_warn:
                warnings.append({"code": "b2_b3_correlated",
                                 "message": f"rho(B2, B3) = {rho:.2f} > {rc.b3.rho_warn}: hai feature cung do tham nien"})
        if reverse and any(j.status != "open" for j in jds):
            warnings.append({"code": "jd_not_open", "message": "co JD khong con mo trong request"})

        ordered = finalize(scored, rc)                                                      # RR4
        rows = [FeatureRow(cv_id=r.item_id, features=Features(**r.used), missing=r.missing,
                           resp_detail=extra[r.item_id]["resp_detail"], req_detail=extra[r.item_id]["req_detail"],
                           s_raw=round(r.s_raw, 6), gate_cap=r.gate_cap, score=r.score, flags=r.flags)
                for r in ordered]
        top = ordered[: request.N]
        items = [self._final_item(r, *ctx[r.item_id], extra[r.item_id], reverse) for r in top]   # RR6
        timings["total_s"] = round(time.perf_counter() - t0, 4)
        if write:
            self._write(conn, request, ordered, rows, items, timings, ref_ym, extra, stats)
        return RerankOutput(request.run_id, items, rows, timings, warnings, stats)

    # ----------------------------------------------------------------- RR6

    def _name(self, sid: str) -> str:
        s = self.snapshot.skills.get(sid)
        return s.name if s else sid

    @staticmethod
    def _facts(details: list[SentenceDetail], texts: dict[int, str]) -> list[SentenceFact]:
        return [SentenceFact(resp_id=d.resp_idx, resp_text=texts.get(d.resp_idx, ""), level=d.level,
                             evidence_id=d.evidence_id or (str(d.bullet_id) if d.bullet_id is not None else None),
                             matched_words=d.matched_words, missing_words=d.missing_words) for d in details]

    def _final_item(self, r: Scored, jd: JdData, c: CvData, ex: dict, reverse: bool) -> FinalItem:
        facts = a1_a2.skill_facts(jd.skills, c.skills, self.rels.relation)
        resp_facts = self._facts(ex["resp_detail"], {s["idx"]: s["text_raw"] for s in jd.resp})
        req_facts = self._facts(ex["req_detail"], {s["idx"]: s["text_raw"] for s in jd.req_items})
        bullets = {str(b["bullet_id"]): b for b in c.bullets}
        summ = {f"summary[{s['idx']}]": s for s in c.summary}
        evidence: dict[str, Evidence] = {}
        ev_ids = [f.evidence_id for f in resp_facts + req_facts if f.evidence_id] + [m.evidence_id for m in facts.met]
        for eid in ev_ids:
            if eid in bullets:
                b = bullets[eid]
                evidence[eid] = Evidence(text_raw=b["text_raw"], section=b["section"], item_idx=b["item_idx"],
                                         flags=_bullet_flags(b))
            elif eid in summ:
                s = summ[eid]
                evidence[eid] = Evidence(text_raw=s["text_raw"], section="summary", item_idx=0, flags=_bullet_flags(s))
        gaps = [self._name(s) for s in facts.missing]
        gaps += [f.resp_text for f in resp_facts + req_facts if f.level == "not_evidenced"]
        words = []
        for f in resp_facts:
            if f.level == "partial":
                words += [w for w in f.missing_words if w not in words]
        gaps += words[:_MAX_GAP_WORDS]
        y = ex["relevant_years"]
        exp = ExperienceFacts(relevant_years=round(y, 1) if y is not None else None,
                              level_cv=ex["level_cv"] if ex["level_cv"] is not None else c.meta.get("level_rank"),
                              level_jd=jd.meta.get("level_rank"), level_source=ex["level_source"],
                              edu_fit=round(ex["edu_fit"], 4) if ex["edu_fit"] is not None else None,
                              role_group_cv=c.meta.get("role_group"), role_group_jd=jd.meta.get("role_group"))
        return FinalItem(cv_id=c.cv_id, jd_id=jd.jd_id if reverse else None, jd_version=jd.version if reverse else None,
                         rank=r.rank, score=r.score, score_raw=round(r.s_raw, 6), gate_cap=r.gate_cap,
                         cap_applied=r.cap_applied, features=Features(**r.used), missing=r.missing,
                         skill_facts=facts, resp_facts=resp_facts, req_facts=req_facts, experience_facts=exp,
                         gaps=gaps, evidence=evidence, flags=list(r.flags))

    def _write(self, conn, request: RerankRequest, ordered: list[Scored], rows: list[FeatureRow],
               items: list[FinalItem], timings: dict, ref_ym: str, extra: dict, stats: dict) -> None:
        cfg_json = {"rerank": self.rc.model_dump(mode="json"), "ref_ym": ref_ym, "direction": request.direction,
                    "jd_id": request.jd_id, "jd_version": request.jd_version, "cv_id": request.cv_id,
                    "ontology_version": self.snapshot.ontology_version,
                    # du bo khoa phien ban (thiet ke 00 muc 3.4) + cau hinh BERTScore da dung (T13)
                    "versions": self.cfg.versions.model_dump(), "bertscore": self.cfg.bertscore.model_dump(mode="json"),
                    "stats": stats}
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
                                 "score": f.score, "relevant_years": extra[f.cv_id]["relevant_years"],
                                 "level_cv": extra[f.cv_id]["level_cv"], "level_source": extra[f.cv_id]["level_source"],
                                 "edu_fit": extra[f.cv_id]["edu_fit"]}),
                          f.s_raw, f.gate_cap) for f in rows])
            insert_rows(cur, "rerank_result",
                        ("run_id", "item_id", "rank", "score", "score_raw", "cap_applied", "facts_json"),
                        [(request.run_id, it.jd_id or it.cv_id, it.rank, it.score, it.score_raw, it.cap_applied,
                          Jsonb(it.model_dump(mode="json"))) for it in items])
