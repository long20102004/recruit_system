"""EX1: lay / dung `FinalItem` cho (rerank run, cv_id) (thiet ke 08 muc 1, 2).

CV trong top N: doc nguyen `rerank_result.facts_json` (Rerank da dung o RR6).
CV ngoai top N (HR mo xem CV hang 150): dung lai tu `rerank_feature` + `cv_skill` + `cv_bullet` + bang JD.
Explain khong import rerank (chi giao tiep qua Postgres + core/contracts) nen phan nay tu lam.
"""

from __future__ import annotations

import psycopg

from cvmatch.core.contracts import (
    Evidence, ExperienceFacts, Features, FinalItem, SentenceFact, SkillFacts, SkillMet, SkillPartial,
)
from cvmatch.core.kb.rel import SkillRelations

_MAX_GAP_WORDS = 10


class FactsNotFound(Exception):
    pass


def _skill_facts(jd_skills: list[dict], cv_skills: dict[str, dict], rels: SkillRelations | None) -> SkillFacts:
    reqs: dict[object, list[str]] = {}
    for s in jd_skills:
        if s["required"]:
            key = ("g", s["group_id"]) if s["group_id"] is not None else ("s", s["skill_id"])
            reqs.setdefault(key, []).append(s["skill_id"])
    facts = SkillFacts()
    for opts in reqs.values():
        hits = [cv_skills[o] for o in opts if o in cv_skills]
        if hits:
            h = max(hits, key=lambda s: (s["ev"], s["skill_id"]))
            eid = str(h["bullet_id"]) if h["bullet_id"] is not None else h["source_field"]
            facts.met.append(SkillMet(skill=h["skill_id"], ev=h["ev"], evidence_id=eid))
            continue
        part = None
        if rels is not None:
            for s in sorted(cv_skills.values(), key=lambda s: (-s["ev"], s["skill_id"])):
                r = next(((o, rels.relation(s["skill_id"], o)) for o in opts
                          if rels.relation(s["skill_id"], o) in ("parent", "child", "sibling")), None)
                if r:
                    part = SkillPartial(required=r[0], found=s["skill_id"], relation=r[1])
                    break
        if part:
            facts.partial.append(part)
        else:
            facts.missing.append(opts[0])
    return facts


def load_final_item(conn: psycopg.Connection, run_id: str, cv_id: str, *,
                    rels: SkillRelations | None = None, names: dict[str, str] | None = None) -> FinalItem:
    row = conn.execute("SELECT facts_json FROM rerank_result WHERE run_id = %s AND item_id = %s",
                       (run_id, cv_id)).fetchone()
    if row is not None:
        return FinalItem.model_validate(row["facts_json"])
    run = conn.execute("SELECT config_json FROM rerank_run WHERE run_id = %s", (run_id,)).fetchone()
    feat = conn.execute("SELECT * FROM rerank_feature WHERE run_id = %s AND item_id = %s", (run_id, cv_id)).fetchone()
    if run is None or feat is None:
        raise FactsNotFound(f"khong co ket qua rerank cho CV {cv_id} trong run {run_id}")
    cj = run["config_json"]
    if cj.get("direction") == "cv_to_jd":                 # item = jd_id, CV truy van o config_json
        jd_id = cv_id
        ver = int((feat["detail_json"] or {}).get("jd_version") or conn.execute(
            "SELECT version FROM jd WHERE jd_id = %s AND is_latest", (jd_id,)).fetchone()["version"])
        cv_id = cj["cv_id"]
    else:
        jd_id, ver = cj["jd_id"], cj["jd_version"]
    detail = feat["detail_json"]
    jd_skills = conn.execute("SELECT skill_id, required, group_id FROM jd_skill WHERE jd_id=%s AND version=%s"
                             " ORDER BY required DESC, w_imp DESC, skill_id", (jd_id, ver)).fetchall()
    resp_text = {r["idx"]: r["text_raw"] for r in conn.execute(
        "SELECT idx, text_raw FROM jd_responsibility WHERE jd_id=%s AND version=%s", (jd_id, ver))}
    req_text = {r["idx"]: r["text_raw"] for r in conn.execute(
        "SELECT idx, text_raw FROM jd_requirement_item WHERE jd_id=%s AND version=%s", (jd_id, ver))}
    jd_meta = conn.execute("SELECT role_group, level_rank FROM jd_meta WHERE jd_id=%s AND version=%s",
                           (jd_id, ver)).fetchone() or {}
    cv_skills = {r["skill_id"]: {**r, "ev": float(r["ev"])} for r in conn.execute(
        "SELECT skill_id, ev, bullet_id, source_field FROM cv_skill WHERE cv_id = %s", (cv_id,))}
    bullets = {r["bullet_id"]: r for r in conn.execute(
        "SELECT bullet_id, section, item_idx, text_raw, has_negation, is_coursework FROM cv_bullet WHERE cv_id = %s",
        (cv_id,))}
    cv_meta = conn.execute("SELECT role_group, level_rank FROM cv_meta WHERE cv_id = %s", (cv_id,)).fetchone() or {}
    summary = {f"summary[{r['idx']}]": r for r in conn.execute(
        "SELECT idx, text_raw, has_negation, is_coursework FROM cv_summary_sentence WHERE cv_id = %s", (cv_id,))}

    facts = _skill_facts(jd_skills, cv_skills, rels)
    def sfacts(key: str, texts: dict) -> list[SentenceFact]:
        return [SentenceFact(resp_id=d["resp_idx"], resp_text=texts.get(d["resp_idx"], ""), level=d["level"],
                             evidence_id=d.get("evidence_id") or (str(d["bullet_id"]) if d["bullet_id"] is not None
                                                                  else None),
                             matched_words=d["matched_words"], missing_words=d["missing_words"])
                for d in detail.get(key, [])]

    resp_facts = sfacts("resp_detail", resp_text)
    req_facts = sfacts("req_detail", req_text)
    evidence = {}
    for eid in [f.evidence_id for f in resp_facts + req_facts if f.evidence_id] + [m.evidence_id for m in facts.met]:
        if eid.isdigit() and int(eid) in bullets:
            b = bullets[int(eid)]
            evidence[eid] = Evidence(text_raw=b["text_raw"], section=b["section"], item_idx=b["item_idx"],
                                     flags=[f for f in ("has_negation", "is_coursework") if b[f]])
        elif eid in summary:
            s = summary[eid]
            evidence[eid] = Evidence(text_raw=s["text_raw"], section="summary", item_idx=0,
                                     flags=[f for f in ("has_negation", "is_coursework") if s[f]])
    nm = names or {}
    gaps = [nm.get(s, s) for s in facts.missing] + [f.resp_text for f in resp_facts + req_facts
                                                     if f.level == "not_evidenced"]
    words: list[str] = []
    for f in resp_facts:
        if f.level == "partial":
            words += [w for w in f.missing_words if w not in words]
    gaps += words[:_MAX_GAP_WORDS]
    years = detail.get("relevant_years")
    gate = int(feat["gate_cap"])
    s_raw = float(feat["s_raw"])
    return FinalItem(
        cv_id=cv_id, jd_id=jd_id if cj.get("direction") == "cv_to_jd" else None,
        jd_version=ver if cj.get("direction") == "cv_to_jd" else None, rank=int(detail.get("rank", 0)), score=int(detail.get("score", 0)), score_raw=round(s_raw, 6),
        gate_cap=gate, cap_applied=100 * s_raw > gate, features=Features(**feat["features_json"]),
        missing=feat["missing_json"], skill_facts=facts, resp_facts=resp_facts, req_facts=req_facts,
        experience_facts=ExperienceFacts(relevant_years=round(years, 1) if years is not None else None,
                                         level_cv=detail.get("level_cv") if detail.get("level_cv") is not None
                                         else cv_meta.get("level_rank"), level_jd=jd_meta.get("level_rank"),
                                         level_source=detail.get("level_source"), edu_fit=detail.get("edu_fit"),
                                         role_group_cv=cv_meta.get("role_group"),
                                         role_group_jd=jd_meta.get("role_group")),
        gaps=gaps, evidence=evidence, flags=list(detail.get("flags", [])))
