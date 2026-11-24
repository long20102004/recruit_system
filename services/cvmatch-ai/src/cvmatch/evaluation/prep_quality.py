"""Do chat luong tien xu ly (thiet ke 03 "Do chat luong tien xu ly", 09 muc 1 tang 0).

1. `export_sample`: lay mau 50 CV + 30 JD tu DB -> file JSONL cho nguoi kiem tay. Moi dong co phan
   `system` (he thong trich ra) va phan `gold` de TRONG cho nguoi kiem dien:
     CV: skills (ten ky nang KB), years_experience, role_group, level_rank
     JD: skills (bat buoc), min_years, role_group, level_rank
   Van ban dua cho nguoi kiem la ban DA AN DANH (anon_json / norm_json), khong lay raw_json.
2. `score_sample`: doc file da dien -> precision / recall ky nang (vi mo tren tat ca tai lieu), sai so
   tuyet doi trung binh `years_experience` / `min_years`, ti le dung `role_group` va `level_rank`.
"""

from __future__ import annotations

import json
import random
from pathlib import Path


def export_sample(conn, out_path: str | Path, *, n_cv: int = 50, n_jd: int = 30, seed: int = 13,
                  names: dict[str, str] | None = None) -> dict:
    rng = random.Random(seed)
    names = names or {}
    cv_ids = [str(r["cv_id"]) for r in conn.execute(
        "SELECT cv_id FROM cv WHERE status = 'active' AND is_latest ORDER BY cv_id")]
    jd_keys = [(r["jd_id"], r["version"]) for r in conn.execute(
        "SELECT jd_id, version FROM jd WHERE is_latest ORDER BY jd_id")]
    cv_pick = sorted(rng.sample(cv_ids, min(n_cv, len(cv_ids))))
    jd_pick = sorted(rng.sample(jd_keys, min(n_jd, len(jd_keys))))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with Path(out_path).open("w", encoding="utf-8") as f:
        for cid in cv_pick:
            cv = conn.execute("SELECT anon_json FROM cv WHERE cv_id = %s", (cid,)).fetchone()
            meta = conn.execute("SELECT years_experience, role_group, level_rank FROM cv_meta WHERE cv_id = %s",
                                (cid,)).fetchone() or {}
            skills = sorted(names.get(r["skill_id"], r["skill_id"]) for r in conn.execute(
                "SELECT skill_id FROM cv_skill WHERE cv_id = %s", (cid,)))
            rec = {"kind": "cv", "id": cid, "text": cv["anon_json"],
                   "system": {"skills": skills,
                              "years_experience": float(meta["years_experience"]) if meta.get("years_experience") is not None else None,
                              "role_group": meta.get("role_group"), "level_rank": meta.get("level_rank")},
                   "gold": {"skills": None, "years_experience": None, "role_group": None, "level_rank": None}}
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            n += 1
        for jid, ver in jd_pick:
            jd = conn.execute("SELECT norm_json FROM jd WHERE jd_id = %s AND version = %s", (jid, ver)).fetchone()
            meta = conn.execute("SELECT min_years, role_group, level_rank FROM jd_meta WHERE jd_id = %s AND version = %s",
                                (jid, ver)).fetchone() or {}
            skills = sorted(names.get(r["skill_id"], r["skill_id"]) for r in conn.execute(
                "SELECT skill_id FROM jd_skill WHERE jd_id = %s AND version = %s AND required", (jid, ver)))
            rec = {"kind": "jd", "id": f"{jid}@{ver}", "text": jd["norm_json"],
                   "system": {"skills": skills,
                              "min_years": float(meta["min_years"]) if meta.get("min_years") is not None else None,
                              "role_group": meta.get("role_group"), "level_rank": meta.get("level_rank")},
                   "gold": {"skills": None, "min_years": None, "role_group": None, "level_rank": None}}
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            n += 1
    return {"n_cv": len(cv_pick), "n_jd": len(jd_pick), "rows": n}


def score_sample(path: str | Path) -> dict:
    out: dict = {}
    recs = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    for kind, years_key in (("cv", "years_experience"), ("jd", "min_years")):
        rs = [r for r in recs if r["kind"] == kind]
        tp = fp = fn = 0
        errs, role_ok, role_n, lvl_ok, lvl_n, n_checked = [], 0, 0, 0, 0, 0
        for r in rs:
            g, s = r.get("gold") or {}, r.get("system") or {}
            if g.get("skills") is not None:
                n_checked += 1
                gs = {x.strip().lower() for x in g["skills"]}
                ss = {x.strip().lower() for x in s.get("skills") or []}
                tp += len(gs & ss)
                fp += len(ss - gs)
                fn += len(gs - ss)
            if g.get(years_key) is not None and s.get(years_key) is not None:
                errs.append(abs(float(g[years_key]) - float(s[years_key])))
            if g.get("role_group") is not None:
                role_n += 1
                role_ok += int(g["role_group"] == s.get("role_group"))
            if g.get("level_rank") is not None:
                lvl_n += 1
                lvl_ok += int(int(g["level_rank"]) == (s.get("level_rank") if s.get("level_rank") is None
                                                       else int(s["level_rank"])))
        out[kind] = {
            "n": len(rs), "n_skills_checked": n_checked,
            "skill_precision": tp / (tp + fp) if tp + fp else None,
            "skill_recall": tp / (tp + fn) if tp + fn else None,
            f"{years_key}_mae": sum(errs) / len(errs) if errs else None,
            "role_group_acc": role_ok / role_n if role_n else None,
            "level_rank_acc": lvl_ok / lvl_n if lvl_n else None,
        }
    return out
