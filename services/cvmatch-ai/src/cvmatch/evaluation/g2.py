"""G2: chay lai cac golden test co diem yeu qua CA pipeline (thiet ke 09 muc 4.2).

Moi test -> mot JD (trach nhiem = cau JD cua test) + moi bien the mot CV (gach = cau CV), nap bang Luong A/B,
Rerank -> doc `c_j` / `R_best` cua B4. Ky vong dat TRUOC:

| Test | Ky vong sau pipeline |
| T05 phu dinh | c_j gach phu dinh <= 0,3 nho m_neg |
| T04 hoc / lam | gach hoc tap co co is_coursework; c_j(real) > c_j(student) va khoang cach tang so voi R tran |
| T06 viet tat | (R(pos) - R(neg)) sau doi alias "K8s" -> "Kubernetes" > ban tran |
| T08 so nam | |R(5y) - R(1y)| <= 2% span sau che so (so nam do B2 cham) |
| T11, F05 khong dau | CV co co `no_diacritics`, B4 thieu phia CV (khong bi diem thap) |
| T19 truu tuong | ghi nhan (xem R-E10) |

"Ban tran" tinh bang CUNG encoder voi `canonicalize_aliases = mask_numbers = false` (FakeEncoder hay bge-m3 deu so
duoc voi chinh no). Span = R(T23 trung hoan toan) - R(T10 khong lien quan) cua ban pipeline.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from cvmatch.core.kb.matcher import SkillMatcher
from cvmatch.evaluation.golden.data import GOLDEN
from cvmatch.rerank.bertscore.cache import TokenCache
from cvmatch.rerank.bertscore.engine import BertScorer

CASES = ("T04", "T05", "T06", "T08", "T11", "F05", "T19")


def _cv(tag: str, bullets: list[str], title: str = "Software Engineer") -> dict:
    return {"full_name": f"G2 {tag}", "email": f"g2-{tag.lower()}@example.com", "summary": "",
            "experiences": [{"title": title, "start": "2021-01", "is_current": True, "description": list(bullets)}],
            "projects": [], "education": [], "skills": []}


def _jd(tid: str, sents: list[str]) -> dict:
    return {"jd_id": f"G2-{tid}", "title": "Software Engineer", "responsibilities": list(sents), "skills": [],
            "requirements": []}


@dataclass
class G2Row:
    id: str
    passed: bool | None
    message: str
    detail: dict


def _bare(scorer: BertScorer) -> BertScorer:
    cfg = scorer.cfg.model_copy(update={"canonicalize_aliases": False, "mask_numbers": False})
    return BertScorer(scorer.encoder, cfg, scorer.matcher, TokenCache(cfg.key()))


def run_g2(svc, *, ref_ym: str | None = None) -> list[G2Row]:
    gold = {g["id"]: g for g in GOLDEN}
    scorer = svc.scorer
    bare = _bare(scorer)
    span = float(scorer.recall_matrix(["Xây dựng API backend"], ["Xây dựng API backend"])[0, 0]
                 - scorer.recall_matrix(gold["T10"]["jd"], gold["T10"]["variants"]["unrelated"])[0, 0]) or 1.0
    rows: list[G2Row] = []
    for tid in CASES:
        g = gold[tid]
        cvs = {v: _cv(f"{tid}-{v}", texts) for v, texts in g["variants"].items()}
        outs = svc.ingest_cvs([(f"{tid}:{v}", copy.deepcopy(c)) for v, c in cvs.items()])
        ids = {v: o.cv_id for v, o in zip(cvs, outs)}
        jd = _jd(tid, g["jd"])
        svc.ingest_jd(copy.deepcopy(jd))
        m = svc.match_jd(jd["jd_id"], K=len(svc.index.cv_ids), N=len(svc.index.cv_ids), ref_ym=ref_ym)
        with svc.connect() as conn:
            feat = {r["item_id"]: r for r in conn.execute(
                "SELECT item_id, features_json, missing_json, detail_json FROM rerank_feature WHERE run_id = %s",
                (m.run_id,)) if r["item_id"] in ids.values()}
            flags = {str(r["cv_id"]): list(r["flags"] or []) for r in conn.execute(
                "SELECT cv_id, flags FROM cv WHERE cv_id = ANY(%s::uuid[])", (list(ids.values()),))}
            bflags = {str(r["cv_id"]): r for r in conn.execute(
                "SELECT cv_id, bool_or(has_negation) AS neg, bool_or(is_coursework) AS course FROM cv_bullet"
                " WHERE cv_id = ANY(%s::uuid[]) GROUP BY cv_id", (list(ids.values()),))}

        def c(v):
            d = feat[ids[v]]["detail_json"]["resp_detail"]
            return max((x["c_j"] for x in d), default=None)

        def R(v):
            d = feat[ids[v]]["detail_json"]["resp_detail"]
            return max((x["R_best"] for x in d), default=None)

        def Rb(v):
            return float(bare.recall_matrix(g["jd"], g["variants"][v]).max(axis=1).mean())

        det = {v: {"c_j": c(v) if feat[ids[v]]["detail_json"]["resp_detail"] else None,
                   "R": R(v) if feat[ids[v]]["detail_json"]["resp_detail"] else None,
                   "R_bare": Rb(v), "flags": flags.get(ids[v], []),
                   "B4_missing": feat[ids[v]]["missing_json"].get("B4")} for v in cvs}
        if tid == "T05":
            ok = det["negation"]["c_j"] is not None and det["negation"]["c_j"] <= 0.3 and \
                bool(bflags.get(ids["negation"], {}).get("neg"))
            msg = f"c_j(negation) = {det['negation']['c_j']} (<= 0,3), has_negation = {bflags.get(ids['negation'], {}).get('neg')}"
        elif tid == "T04":
            gap = (det["real"]["c_j"] or 0) - (det["student"]["c_j"] or 0)
            gap_b = (det["real"]["R_bare"] - det["student"]["R_bare"]) / span
            course = bool(bflags.get(ids["student"], {}).get("course"))
            ok = course and gap > 0
            msg = (f"is_coursework = {course}; c_j real - student = {gap:+.3f} (thang c) · ban tran R = {gap_b:+.1%} span")
        elif tid == "T06":
            d_p = (det["pos"]["R"] - det["neg"]["R"]) / span
            d_b = (det["pos"]["R_bare"] - det["neg"]["R_bare"]) / span
            ok = d_p > d_b
            msg = f"pos - neg: pipeline {d_p:+.1%} span so voi tran {d_b:+.1%} span"
        elif tid == "T08":
            d = abs(det["5y"]["R"] - det["1y"]["R"]) / span
            ok = d <= 0.02
            msg = f"|R(5y) - R(1y)| = {d:.2%} span (<= 2%); ban tran {(det['5y']['R_bare'] - det['1y']['R_bare']) / span:+.1%}"
        elif tid in ("T11", "F05"):
            v = "variant" if tid == "F05" else None
            if v:
                ok = "no_diacritics" in det[v]["flags"] and det[v]["B4_missing"] == "cv_side"
                msg = f"bien the khong dau: co = {det[v]['flags']}, B4 thieu = {det[v]['B4_missing']}"
            else:   # T11: JD khong dau (CV co dau) -> chi ghi nhan
                ok = None
                msg = f"JD khong dau: c_j pos = {det['pos']['c_j']}, neg = {det['neg']['c_j']} (ghi nhan)"
        else:       # T19
            ok = None
            msg = f"ghi nhan: R pos - neg = {(det['pos']['R'] - det['neg']['R']) / span:+.1%} span (xem R-E10)"
        rows.append(G2Row(tid, ok, msg, det))
    return rows


def to_markdown(rows: list[G2Row], encoder_key: str) -> str:
    mark = {True: "✅", False: "❌", None: "ghi nhận"}
    out = [f"# G2: golden qua cả pipeline (`{encoder_key}`)", "", "| Test | Kết quả | Chi tiết |", "| --- | --- | --- |"]
    out += [f"| {r.id} | {mark[r.passed]} | {r.message} |" for r in rows]
    return "\n".join(out) + "\n"
