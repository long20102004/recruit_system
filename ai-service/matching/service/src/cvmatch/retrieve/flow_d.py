"""Luong D: tu mot CV tim JD dang mo phu hop (thiet ke 06 muc 5, D1-D8).

    D1 tai bieu dien CV (vector, ky nang, gach) - CV phai co trong kho (CV tam: api `POST /match/cv:preview`)
    D2 chi JD open + moi nhat (JdIndex) + loc cung tuy chon (truong thieu -> cho qua)
    D3 dense; BM25 truy van `condensed_cv` | `full_cv` tren chi muc BM25 kho JD;
       ky nang: sum w_imp x ev / max(sum w_imp, reverse.skill.min_imp_sum); trach nhiem: moi trach nhiem
       JD tim gach CV giong nhat -> trung binh theo JD. JD khong co ky nang bat buoc / trach nhiem -> NaN
       (view do khong tinh cho rieng JD do).
    D4 so JD < reverse.min_pool_minmax -> RRF thay min-max
    D5 top K = min(reverse.K_max, so JD mo); so JD <= K -> chuyen het. Hoa: s_skill giam -> jd_id tang
    D6 giai thich so bo   D7 log match_run (direction = cv_to_jd)   D8 RerankRequest (N = rerank.reverse_N)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import numpy as np
import psycopg
from psycopg.types.json import Jsonb

from cvmatch.core.config import AppConfig
from cvmatch.core.contracts import RerankCandidate, RerankRequest, ViewScores
from cvmatch.core.db import insert_rows, transaction
from cvmatch.core.text.bm25_tokens import skill_tokens, tokens_acc, tokens_noacc
from cvmatch.retrieve import fusion
from cvmatch.retrieve.jd_index import JdIndex

VIEWS = ("dense", "bm25", "skill", "resp")


class CvNotReady(Exception):
    """CV khong co / da xoa / khac bo phien ban voi kho JD."""


@dataclass
class CvData:
    cv_id: str
    dense: np.ndarray
    skills: dict[str, float]                 # skill_id -> ev
    bullet_ids: list[int]
    bullet_text: list[str]
    bullet_dense: np.ndarray
    bm25_full: list[str]
    titles: list[str]
    recent_text: str
    meta: dict


@dataclass
class ReverseResult:
    run_id: str
    cv_id: str
    n_pool: int
    items: list[dict]                        # jd_id, version, rank, s, n, fused, explanation
    warnings: list[dict]
    views_used: list[str]
    fusion: str
    request: RerankRequest


def load_cv(conn: psycopg.Connection, cv_id: str, versions: tuple) -> CvData:
    row = conn.execute("SELECT status, is_latest, ontology_version, pipeline_version, embed_model FROM cv"
                       " WHERE cv_id = %s", (cv_id,)).fetchone()
    if row is None or row["status"] != "active":
        raise CvNotReady(f"khong co CV {cv_id} (hoac da xoa) - chay Luong A truoc")
    if (row["ontology_version"], row["pipeline_version"], row["embed_model"]) != versions:
        raise CvNotReady(f"CV {cv_id} khac bo phien ban kho JD ({row['ontology_version']}, {row['pipeline_version']},"
                         f" {row['embed_model']}) != {versions} - chay lai Luong A (reprocess)")
    with conn.cursor(binary=True) as cur:
        cur.execute("SELECT dense FROM cv_vector WHERE cv_id = %s", (cv_id,))
        dense = cur.fetchone()["dense"].to_numpy().astype(np.float32)
        cur.execute("SELECT b.bullet_id, b.text, b.text_raw, v.dense, b.item_idx, b.section FROM cv_bullet b"
                    " JOIN cv_bullet_vector v USING (bullet_id) WHERE b.cv_id = %s ORDER BY b.section, b.item_idx,"
                    " b.pos", (cv_id,))
        br = cur.fetchall()
    skills = {r["skill_id"]: float(r["ev"]) for r in conn.execute(
        "SELECT skill_id, ev FROM cv_skill WHERE cv_id = %s", (cv_id,))}
    d = conn.execute("SELECT bm25_noacc, bm25_acc, skill_tokens FROM cv_bm25_doc WHERE cv_id = %s", (cv_id,)).fetchone()
    exps = conn.execute("SELECT idx, title_raw FROM cv_experience WHERE cv_id = %s ORDER BY idx", (cv_id,)).fetchall()
    meta = conn.execute("SELECT location, years_experience, role_group FROM cv_meta WHERE cv_id = %s",
                        (cv_id,)).fetchone() or {}
    recent = " ".join(r["text"] for r in br if r["section"] == "experience" and r["item_idx"] == 0)
    return CvData(cv_id=cv_id, dense=dense, skills=skills, bullet_ids=[int(r["bullet_id"]) for r in br],
                  bullet_text=[r["text_raw"] for r in br],
                  bullet_dense=(np.stack([r["dense"].to_numpy() for r in br]).astype(np.float32)
                                if br else np.zeros((0, 1024), np.float32)),
                  bm25_full=list(d["bm25_noacc"] or []) + list(d["skill_tokens"] or []) if d else [],
                  titles=[r["title_raw"] for r in exps if r["title_raw"]], recent_text=recent, meta=dict(meta))


def condensed_query(cv: CvData, segmenter) -> list[str]:
    """`condensed_cv` (06 muc 5.5 b): chuc danh + token ky nang + tu khoa kinh nghiem gan nhat, BO TRUNG."""
    toks = tokens_noacc(tokens_acc(" ".join(cv.titles + [cv.recent_text]), segmenter)) + skill_tokens(cv.skills)
    return list(dict.fromkeys(toks))


def view_skill_jd(idx: JdIndex, cv_skills: dict[str, float], min_imp_sum: float) -> np.ndarray:
    """(c) moi JD: sum_r w_r x max ev(lua chon) / max(sum w_r, min_imp_sum); JD khong co ky nang bat buoc -> NaN."""
    out = np.full(idx.n_jd, np.nan, np.float32)
    for i, reqs in enumerate(idx.reqs):
        if not reqs:
            continue
        total = sum(w for w, _ in reqs)
        num = sum(w * max((cv_skills.get(s, 0.0) for s in opts), default=0.0) for w, opts in reqs)
        out[i] = num / max(total, min_imp_sum)
    return out


def view_resp_jd(idx: JdIndex, bullet_dense: np.ndarray) -> np.ndarray | None:
    """(d) moi trach nhiem JD: max cosine voi gach CV -> trung binh theo JD; JD khong co trach nhiem -> NaN."""
    if not len(bullet_dense) or not len(idx.resp):
        return None
    best = (idx.resp.astype(np.float32) @ bullet_dense.T).max(axis=1)
    out = np.full(idx.n_jd, np.nan, np.float32)
    sums = np.bincount(idx.resp_jd_index, weights=best, minlength=idx.n_jd)
    cnt = np.bincount(idx.resp_jd_index, minlength=idx.n_jd)
    has = cnt > 0
    out[has] = (sums[has] / cnt[has]).astype(np.float32)
    return out


def pool_mask_jd(idx: JdIndex, hard_filters: dict | None, exclude: set[str],
                 include: set[str] | None = None) -> np.ndarray:
    mask = np.ones(idx.n_jd, dtype=bool)
    if include is not None:
        keep = np.zeros_like(mask)
        for j in include:
            if j in idx.row_of:
                keep[idx.row_of[j]] = True
        mask &= keep
    for j in exclude:
        if j in idx.row_of:
            mask[idx.row_of[j]] = False
    if hard_filters:
        for i, m in enumerate(idx.meta):
            if hard_filters.get("location") and m.get("location") and m.get("work_mode") != "remote":
                if m["location"] != hard_filters["location"]:
                    mask[i] = False
            if hard_filters.get("work_mode") and m.get("work_mode") and m["work_mode"] != hard_filters["work_mode"]:
                mask[i] = False
    return mask


def retrieve_for_cv(conn: psycopg.Connection, idx: JdIndex, cfg: AppConfig, cv_id: str, *, K: int | None = None,
                    hard_filters: dict | None = None, exclude_jd_ids: set[str] | None = None,
                    views: list[str] | None = None, segmenter=None, write_log: bool = True,
                    include_jd_ids: set[str] | None = None) -> ReverseResult:
    rc, rv = cfg.retrieve, cfg.retrieve.reverse
    views = list(views or rc.views_enabled)
    cv = load_cv(conn, cv_id, idx.versions)                                                     # D1
    mask = pool_mask_jd(idx, hard_filters, exclude_jd_ids or set(), include_jd_ids)             # D2
    n_pool = int(mask.sum())
    warnings: list[dict] = []
    if include_jd_ids is not None:
        unknown = sorted(j for j in include_jd_ids if j not in idx.row_of)
        if unknown:
            warnings.append({"code": "include_unknown", "message": f"{len(unknown)} JD không mở / không có",
                             "jd_ids": unknown})
    if n_pool == 0:
        warnings.append({"code": "no_open_jd", "message": "Không có JD nào đang mở"})
    if not cv.skills and not cv.bullet_ids:
        warnings.append({"code": "cv_low_info", "message": "CV thiếu thông tin: kết quả kém phân biệt"})

    raw: dict[str, np.ndarray] = {}                                                             # D3
    if "dense" in views and idx.n_jd:
        raw["dense"] = (idx.doc.astype(np.float32) @ cv.dense).astype(np.float32)
    if "bm25" in views and idx.n_jd:
        if rv.bm25_query_mode == "full_cv":
            q = cv.bm25_full
        else:
            if segmenter is None:
                from cvmatch.core.text.segment import make_segmenter
                segmenter = make_segmenter(cfg.prep.segmenter, cfg.prep.protected_tokens)
            q = condensed_query(cv, segmenter)
        if q:
            raw["bm25"] = idx.bm25.scores(q)
    if "skill" in views and idx.n_jd:
        s = view_skill_jd(idx, cv.skills, rv.skill.min_imp_sum)
        if np.isfinite(s).any():
            raw["skill"] = s
    if "resp" in views and idx.n_jd:
        r = view_resp_jd(idx, cv.bullet_dense)
        if r is not None:
            raw["resp"] = r

    use_rrf = rc.fusion == "rrf" or n_pool < rv.min_pool_minmax                                 # D4
    normed = {n: fusion.normalize(x, mask, rc.normalization) for n, x in raw.items()}
    if use_rrf:
        fused = fusion.rrf(raw, mask, rc.rrf_k, rc.view_weights if rc.rrf_weighted else None)
        if n_pool < rv.min_pool_minmax:
            warnings.append({"code": "small_jd_pool_rrf",
                             "message": f"Chỉ {n_pool} JD mở (< {rv.min_pool_minmax}): hợp nhất bằng RRF"})
    else:
        fused = fusion.score_sum(normed, rc.view_weights) if normed else np.full(idx.n_jd, np.nan, np.float32)
    K = K or min(rv.K_max, n_pool)                                                              # D5
    top = fusion.rank(fused, raw.get("skill"), idx.jd_ids, mask, K) if idx.n_jd else np.zeros(0, int)

    def val(d, n, i):
        x = d.get(n)
        return None if x is None or not np.isfinite(x[i]) else float(x[i])

    items = []
    for rnk, i in enumerate(top, start=1):                                                      # D6
        reqs = idx.reqs[i]
        met = sorted({o for _, opts in reqs for o in opts if cv.skills.get(o, 0) > 0})
        missing = sorted({opts[0] for _, opts in reqs if not any(cv.skills.get(o, 0) > 0 for o in opts)})
        jid = idx.jd_ids[i]
        items.append({"jd_id": jid, "version": idx.version_of[jid], "rank": rnk,
                      "s": {n: val(raw, n, i) for n in VIEWS}, "n": {n: val(normed, n, i) for n in VIEWS},
                      "fused": float(fused[i]),
                      "explanation": {"jd_version": idx.version_of[jid], "skills_met": met, "skills_missing": missing}})

    run_id = str(uuid.uuid4())
    if write_log:                                                                               # D7
        ov, pv, em = idx.versions
        with transaction(conn) as cur:
            cur.execute("INSERT INTO match_run(run_id, direction, query_id, query_version, config_json, config_hash,"
                        " k, n_pool, warnings, ontology_version, pipeline_version, embed_model)"
                        " VALUES (%s, 'cv_to_jd', %s, NULL, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (run_id, cv_id, Jsonb(cfg.to_json_dict()), cfg.config_hash(), K, n_pool, Jsonb(warnings),
                         ov, pv, em))
            insert_rows(cur, "match_result",
                        ("run_id", "item_id", "rank", "s_dense", "s_bm25", "s_skill", "s_resp",
                         "n_dense", "n_bm25", "n_skill", "n_resp", "fused", "explanation_json"),
                        [(run_id, it["jd_id"], it["rank"], *(it["s"][n] for n in VIEWS), *(it["n"][n] for n in VIEWS),
                          it["fused"], Jsonb(it["explanation"])) for it in items])

    request = RerankRequest(                                                                    # D8
        direction="cv_to_jd", run_id=str(uuid.uuid4()), retrieve_run_id=run_id, cv_id=cv_id,
        N=cfg.rerank.reverse_N, config_version=cfg.rerank.version, bertscore_config=cfg.bertscore.key(),
        candidates=[RerankCandidate(cv_id=it["jd_id"], version=it["version"], rank=it["rank"], s=ViewScores(**it["s"]),
                                    n=ViewScores(**it["n"]), fused=it["fused"]) for it in items])
    return ReverseResult(run_id, cv_id, n_pool, items, warnings, list(raw), "rrf" if use_rrf else rc.fusion, request)
