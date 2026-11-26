"""Luong C: khi HR yeu cau match mot JD voi kho CV (thiet ke 06 muc 4, buoc C1-C8).

C1 tai du lieu JD (dung bo phien ban) -> C2 lap pool (active + latest, loc cung neu bat; truong
thieu thi CHO QUA) -> C3 cham TOAN KHO 4 goc nhin -> C4 min-max theo JD -> C5 hop nhat, top K ->
C6 giai thich so bo -> C7 ghi match_run / match_result -> C8 tao RerankRequest.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import numpy as np
import psycopg
from psycopg.types.json import Jsonb

from cvmatch.core.config import AppConfig
from cvmatch.core.contracts import RerankCandidate, RerankRequest, ViewScores
from cvmatch.core.db import insert_rows, transaction
from cvmatch.core.text.bm25_tokens import skill_tokens, tokens_acc, tokens_noacc
from cvmatch.retrieve import fusion
from cvmatch.retrieve.index import CvIndex
from cvmatch.retrieve.views import bullet_sims, per_cv_max, view_bm25, view_dense, view_skill

VIEWS = ("dense", "bm25", "skill", "resp")


class JdNotReady(Exception):
    """JD chua co / khac bo phien ban voi kho CV -> phai chay Luong B truoc (C1)."""


@dataclass
class JdData:
    jd_id: str
    version: int
    title: str | None
    dense: np.ndarray
    bm25_tokens: list[str]
    required: list[tuple[str, float, int | None]]
    resp_idx: list[int]
    resp_text: list[str]
    resp_dense: np.ndarray
    meta: dict
    skill_names: list[str] = field(default_factory=list)


@dataclass
class RetrieveResult:
    run_id: str
    jd_id: str
    jd_version: int
    n_pool: int
    items: list[dict]
    warnings: list[dict]
    views_used: list[str]
    request: RerankRequest


# --------------------------------------------------------------------------- C1


def load_jd(conn: psycopg.Connection, jd_id: str, version: int | None, versions: tuple) -> JdData:
    if version:
        row = conn.execute("SELECT * FROM jd WHERE jd_id = %s AND version = %s", (jd_id, version)).fetchone()
    else:   # ban moi nhat CUNG bo khoa phien ban (ban song song sau reprocess), khong thi ban moi nhat
        row = conn.execute("SELECT * FROM jd WHERE jd_id = %s AND ontology_version = %s AND pipeline_version = %s"
                           " AND embed_model = %s ORDER BY version DESC LIMIT 1", (jd_id, *versions)).fetchone() \
            or conn.execute("SELECT * FROM jd WHERE jd_id = %s AND is_latest", (jd_id,)).fetchone()
    if row is None:
        raise JdNotReady(f"khong co JD {jd_id}" + (f" v{version}" if version else "") + " - chay Luong B truoc")
    if (row["ontology_version"], row["pipeline_version"], row["embed_model"]) != versions:
        raise JdNotReady(f"JD {jd_id} v{row['version']} khac bo phien ban kho CV "
                         f"({row['ontology_version']}, {row['pipeline_version']}, {row['embed_model']}) != {versions}"
                         " - chay lai Luong B")
    v = row["version"]
    with conn.cursor(binary=True) as cur:
        cur.execute("SELECT dense, bm25_query_tokens FROM jd_vector WHERE jd_id = %s AND version = %s", (jd_id, v))
        vec = cur.fetchone()
        cur.execute("SELECT idx, text_raw, dense FROM jd_responsibility WHERE jd_id = %s AND version = %s"
                    " AND NOT is_generic ORDER BY idx", (jd_id, v))
        resp = cur.fetchall()
    skills = conn.execute("SELECT skill_id, required, w_imp, group_id FROM jd_skill WHERE jd_id = %s AND version = %s",
                          (jd_id, v)).fetchall()
    meta = conn.execute("SELECT * FROM jd_meta WHERE jd_id = %s AND version = %s", (jd_id, v)).fetchone() or {}
    norm = row["norm_json"] or {}
    return JdData(
        jd_id=jd_id, version=v, title=norm.get("title"),
        dense=vec["dense"].to_numpy().astype(np.float32),
        bm25_tokens=list(vec["bm25_query_tokens"]),
        required=[(s["skill_id"], float(s["w_imp"]), s["group_id"]) for s in skills if s["required"]],
        resp_idx=[r["idx"] for r in resp], resp_text=[r["text_raw"] for r in resp],
        resp_dense=(np.stack([r["dense"].to_numpy() for r in resp]).astype(np.float32)
                    if resp else np.zeros((0, 1024), np.float32)),
        meta=dict(meta),
        skill_names=[(s.get("name") if isinstance(s, dict) else s) for s in norm.get("skills") or []],
    )


# --------------------------------------------------------------------------- C2


def pool_mask(conn: psycopg.Connection, idx: CvIndex, hard_filters: dict | None, exclude: set[str],
              include: set[str] | None = None, only_recommendable: bool = False) -> np.ndarray:
    """`include` (None = ca kho): chi xet cac CV nay (vd ung vien da nop don vao JD).
    `only_recommendable` (S07): chi CV cua ung vien dong y nhan goi y."""
    mask = idx.active.copy()
    if only_recommendable:
        mask &= idx.recommendable
    if include is not None:
        keep = np.zeros_like(mask)
        for c in include:
            i = idx.row_of.get(c)
            if i is not None:
                keep[i] = True
        mask &= keep
    for c in exclude:
        i = idx.row_of.get(c)
        if i is not None:
            mask[i] = False
    if hard_filters:
        ids = [idx.cv_ids[i] for i in np.flatnonzero(mask)]
        rows = conn.execute("SELECT cv_id, location, years_experience FROM cv_meta WHERE cv_id = ANY(%s::uuid[])",
                            (ids,)).fetchall()
        meta = {str(r["cv_id"]): r for r in rows}
        for c in ids:
            m = meta.get(c) or {}
            loc, yrs = m.get("location"), m.get("years_experience")
            ok = True
            if hard_filters.get("location") and loc is not None:           # truong thieu -> cho qua
                ok &= loc in (hard_filters["location"], "remote") if hard_filters.get("allow_remote", True) \
                    else loc == hard_filters["location"]
            if hard_filters.get("min_years") is not None and yrs is not None:
                ok &= float(yrs) >= float(hard_filters["min_years"])
            if not ok:
                mask[idx.row_of[c]] = False
    return mask


# --------------------------------------------------------------------------- C6


def explain_top(conn, idx: CvIndex, jd: JdData, top: np.ndarray, sims: np.ndarray | None) -> dict[int, dict]:
    req_ids = sorted({s for s, _, _ in jd.required})
    sm = idx.skill_matrix
    out: dict[int, dict] = {}
    picked: dict[int, list[tuple[float, int, int]]] = {}
    if sims is not None and len(idx.bullet_cv_index):
        bci = idx.bullet_cv_index
        for i in top:
            rows = np.flatnonzero(bci == i)
            if not len(rows):
                continue
            best = []
            for j in range(sims.shape[1]):
                k = rows[int(np.argmax(sims[rows, j]))]
                best.append((float(sims[k, j]), j, int(idx.bullet_ids[k])))
            picked[int(i)] = sorted(best, reverse=True)[:3]
    texts = {}
    all_b = [b for v in picked.values() for _, _, b in v]
    if all_b:
        texts = {int(r["bullet_id"]): r["text_raw"] for r in conn.execute(
            "SELECT bullet_id, text_raw FROM cv_bullet WHERE bullet_id = ANY(%s)", (all_b,)).fetchall()}
    for i in top:
        row = sm.getrow(int(i))
        have = {s for s in req_ids if s in idx.skill_col and row[0, idx.skill_col[s]] > 0}
        out[int(i)] = {
            "skills_met": sorted(have), "skills_missing": sorted(set(req_ids) - have),
            "top_bullets": [{"resp_idx": jd.resp_idx[j], "resp_text": jd.resp_text[j], "bullet_id": b,
                             "text_raw": texts.get(b), "cosine": round(s, 4)}
                            for s, j, b in picked.get(int(i), [])],
        }
    return out


# --------------------------------------------------------------------------- toan bo Luong C


def _title_skills_tokens(jd: JdData, segmenter) -> list[str]:
    text = " ".join([jd.title or "", *[n for n in jd.skill_names if n]])
    return tokens_noacc(tokens_acc(text, segmenter)) + skill_tokens(s for s, _, _ in jd.required)


def retrieve_for_jd(conn: psycopg.Connection, idx: CvIndex, cfg: AppConfig, jd_id: str, *,
                    version: int | None = None, K: int | None = None, hard_filters: dict | None = None,
                    exclude_cv_ids: set[str] | None = None, views: list[str] | None = None,
                    segmenter=None, write_log: bool = True,
                    include_cv_ids: set[str] | None = None, only_recommendable: bool = False) -> RetrieveResult:
    rc = cfg.retrieve
    K = K or rc.K
    views = list(views or rc.views_enabled)
    jd = load_jd(conn, jd_id, version, idx.versions)                                        # C1
    mask = pool_mask(conn, idx, hard_filters if (hard_filters or rc.hard_filters.enabled) else None,
                     exclude_cv_ids or set(), include_cv_ids, only_recommendable)              # C2
    warnings: list[dict] = []
    if include_cv_ids is not None:
        unknown = sorted(c for c in include_cv_ids if c not in idx.row_of or not idx.active[idx.row_of[c]])
        if unknown:
            warnings.append({"code": "include_unknown", "message": f"{len(unknown)} CV không có trong chỉ mục",
                             "cv_ids": unknown})
    n_pool = int(mask.sum())
    if hard_filters and n_pool < rc.min_pool_warn:
        warnings.append({"code": "small_pool", "message": f"Lọc cứng chỉ còn {n_pool} CV, nên xem lại điều kiện"})

    raw: dict[str, np.ndarray] = {}                                                            # C3
    sims = None
    if "dense" in views:
        raw["dense"] = view_dense(idx, jd.dense)
    if "bm25" in views:
        toks = jd.bm25_tokens
        if rc.bm25.query_mode == "title_skills":
            if segmenter is None:
                from cvmatch.core.text.segment import make_segmenter
                segmenter = make_segmenter(cfg.prep.segmenter, cfg.prep.protected_tokens)
            toks = _title_skills_tokens(jd, segmenter)
        b = view_bm25(idx, toks)
        if b is not None:
            raw["bm25"] = b
    if "skill" in views:
        s = view_skill(idx, jd.required)
        if s is None:
            warnings.append({"code": "no_skill_view", "message": "JD không có kỹ năng bắt buộc: bỏ góc nhìn kỹ năng"})
        else:
            raw["skill"] = s
    if "resp" in views:
        if len(jd.resp_dense):
            sims = bullet_sims(idx, jd.resp_dense)
            best = per_cv_max(idx, sims)
            if rc.resp_calib is not None:          # T15: hieu chuan lo/hi truoc khi lay trung binh
                lo, hi = rc.resp_calib.lo, rc.resp_calib.hi
                best = np.clip((best - lo) / (hi - lo), 0.0, 1.0)
            raw["resp"] = best.mean(axis=1)
        else:
            warnings.append({"code": "no_resp_view", "message": "JD không có trách nhiệm cụ thể: bỏ góc nhìn trách nhiệm"})

    if rc.fusion == "rrf":                                                                     # C4-C5
        normed = {n: fusion.normalize(x, mask, rc.normalization) for n, x in raw.items()}
        fused = fusion.rrf(raw, mask, rc.rrf_k, rc.view_weights if rc.rrf_weighted else None)
    else:
        normed = {n: fusion.normalize(x, mask, rc.normalization) for n, x in raw.items()}
        fused = fusion.score_sum(normed, rc.view_weights) if normed else np.full(idx.n_cv, np.nan, np.float32)
    top = fusion.rank(fused, raw.get("skill"), idx.cv_ids, mask, K)
    expl = explain_top(conn, idx, jd, top, sims)                                               # C6

    def val(d, n, i):
        x = d.get(n)
        return None if x is None or not np.isfinite(x[i]) else float(x[i])

    items = []
    for r, i in enumerate(top, start=1):
        items.append({"cv_id": idx.cv_ids[i], "rank": r,
                      "s": {n: val(raw, n, i) for n in VIEWS}, "n": {n: val(normed, n, i) for n in VIEWS},
                      "fused": float(fused[i]), "explanation": expl[int(i)]})

    run_id = str(uuid.uuid4())
    if write_log:                                                                              # C7
        ov, pv, em = idx.versions
        with transaction(conn) as cur:
            cur.execute("INSERT INTO match_run(run_id, direction, query_id, query_version, config_json, config_hash,"
                        " k, n_pool, warnings, ontology_version, pipeline_version, embed_model)"
                        " VALUES (%s, 'jd_to_cv', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (run_id, jd_id, jd.version, Jsonb(cfg.to_json_dict()), cfg.config_hash(), K, n_pool,
                         Jsonb(warnings), ov, pv, em))
            insert_rows(cur, "match_result",
                        ("run_id", "item_id", "rank", "s_dense", "s_bm25", "s_skill", "s_resp",
                         "n_dense", "n_bm25", "n_skill", "n_resp", "fused", "explanation_json"),
                        [(run_id, it["cv_id"], it["rank"], *(it["s"][n] for n in VIEWS), *(it["n"][n] for n in VIEWS),
                          it["fused"], Jsonb(it["explanation"])) for it in items])

    request = RerankRequest(                                                                   # C8
        direction="jd_to_cv", run_id=str(uuid.uuid4()), retrieve_run_id=run_id, jd_id=jd_id, jd_version=jd.version,
        N=cfg.rerank.N, config_version=cfg.rerank.version, bertscore_config=cfg.bertscore.key(),
        candidates=[RerankCandidate(cv_id=it["cv_id"], rank=it["rank"], s=ViewScores(**it["s"]),
                                    n=ViewScores(**it["n"]), fused=it["fused"]) for it in items])
    return RetrieveResult(run_id, jd_id, jd.version, n_pool, items, warnings, list(raw), request)
