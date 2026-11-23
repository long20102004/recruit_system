"""Explain chay LUOI (thiet ke 08 muc 2): chi tao khi HR mo chi tiet mot CV, cache theo
`hash(facts, template_version)` trong `rerank_result.explanation_json`.

`Explainer` la interface chung; T17 them ban LLM (`explain.mode = llm`) sau cung interface nay.
"""

from __future__ import annotations

import hashlib
import json
from typing import Protocol

import psycopg
from psycopg.types.json import Jsonb

from cvmatch.core.config import AppConfig
from cvmatch.core.contracts import FinalItem
from cvmatch.core.kb.matcher import SkillMatcher
from cvmatch.core.kb.rel import SkillRelations
from cvmatch.core.kb.snapshot import KBSnapshot
from cvmatch.explain import checks
from cvmatch.explain.facts import load_final_item
from cvmatch.explain.template import build_context, render


def band_of(score: int, cfg: AppConfig) -> str:
    hi, mid = cfg.rerank.score.bands
    return "high" if score >= hi else "mid" if score >= mid else "low"


def cache_key(item: FinalItem, version: str) -> str:
    blob = json.dumps(item.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{version}\n{blob}".encode("utf-8")).hexdigest()


class Explainer(Protocol):
    version: str

    def explain(self, item: FinalItem, *, cv_evidence: set[str] | None = None,
                allowed_skills: set[str] | None = None) -> dict: ...


class TemplateExplainer:
    """Mau xac dinh (P1). Loi kiem tra EX4 voi mau = bug -> raise ExplainCheckError."""

    def __init__(self, cfg: AppConfig, snapshot: KBSnapshot, matcher: SkillMatcher | None = None, *,
                 audience: str = "hr"):
        self.cfg = cfg
        self.ec = cfg.explain
        self.audience = audience
        cand = audience == "candidate"
        self.version = self.ec.candidate_template_version if cand else self.ec.template_version
        self.names = {sid: s.name for sid, s in snapshot.skills.items()}
        self.matcher = matcher or SkillMatcher(snapshot)
        self.template_path = cfg.config_dir / (self.ec.candidate_template_file if cand else self.ec.template_file)
        self.forbidden = checks.load_forbidden(cfg.config_dir / self.ec.forbidden_file)

    def explain(self, item: FinalItem, *, cv_evidence: set[str] | None = None,
                allowed_skills: set[str] | None = None) -> dict:
        band = band_of(item.score, self.cfg)
        label = getattr(self.ec.band_labels, band)
        ctx = build_context(item, self.names, band, label, max_examples=self.ec.max_examples,
                            max_questions=self.ec.max_questions)
        out = render(ctx, self.template_path)
        cited = [e["evidence_id"] for e in ctx["resp"]["examples"]] + [e["evidence_id"] for e in ctx["req"]["examples"]]
        problems = checks.find_problems(
            out.text, out.masked, cited_evidence=cited,
            cv_evidence=cv_evidence if cv_evidence is not None else set(item.evidence),
            cap_applied=item.cap_applied, forbidden=self.forbidden, matcher=self.matcher,
            allowed_skills=allowed_skills)
        if problems:
            raise checks.ExplainCheckError(problems)
        return {"mode": "template", "audience": self.audience, "template_version": self.version,
                "cache_key": cache_key(item, self.version), "cv_id": item.cv_id, "jd_id": item.jd_id,
                "score": item.score, "band": band, "band_label": label,
                "cap_applied": item.cap_applied, "text": out.text, "sections": ctx}


class ExplainService:
    def __init__(self, cfg: AppConfig, snapshot: KBSnapshot, explainer: Explainer | None = None):
        if cfg.explain.mode != "template" and explainer is None:
            raise NotImplementedError("explain.mode = llm lam o T17")
        self.explainer = explainer or TemplateExplainer(cfg, snapshot)
        self.candidate = TemplateExplainer(cfg, snapshot, getattr(self.explainer, "matcher", None), audience="candidate")
        self.rels = SkillRelations.from_config(snapshot, cfg.rerank.rel)
        self.names = {sid: s.name for sid, s in snapshot.skills.items()}

    def explain(self, conn: psycopg.Connection, run_id: str, item_id: str, *, force: bool = False) -> dict:
        """`item_id`: cv_id (chieu jd_to_cv, giai thich cho HR) hoac jd_id (cv_to_jd, giai thich cho ung vien)."""
        run = conn.execute("SELECT direction, config_json FROM rerank_run WHERE run_id = %s", (run_id,)).fetchone()
        reverse = run is not None and run["direction"] == "cv_to_jd"
        item = load_final_item(conn, run_id, item_id, rels=self.rels, names=self.names)
        explainer = self.candidate if reverse else self.explainer
        cv_id = item.cv_id
        key = cache_key(item, explainer.version)
        row = conn.execute("SELECT explanation_json FROM rerank_result WHERE run_id = %s AND item_id = %s",
                           (run_id, item_id)).fetchone()
        cached = row["explanation_json"] if row else None
        if not force and cached and cached.get("cache_key") == key:
            return cached
        cv_evidence = {str(r["bullet_id"]) for r in conn.execute(
            "SELECT bullet_id FROM cv_bullet WHERE cv_id = %s", (cv_id,))}
        cv_evidence |= {f"summary[{r['idx']}]" for r in conn.execute(
            "SELECT idx FROM cv_summary_sentence WHERE cv_id = %s", (cv_id,))}
        cv_evidence |= {m.evidence_id for m in item.skill_facts.met}
        if reverse:
            jd_id, ver = item.jd_id, item.jd_version
        else:
            jd_id, ver = run["config_json"]["jd_id"], run["config_json"]["jd_version"]
        allowed = {r["skill_id"] for r in conn.execute(
            "SELECT skill_id FROM jd_skill WHERE jd_id=%s AND version=%s UNION SELECT skill_id FROM cv_skill"
            " WHERE cv_id = %s", (jd_id, ver, cv_id))}
        # tu lay tu chinh cau JD (vd "chua thay phan: Figma" trong trach nhiem) la noi dung JD, khong phai bia:
        # cong nghe nhac trong trach nhiem / yeu cau cua JD cung duoc phep
        m = getattr(explainer, "matcher", None)
        if m is not None:
            for r in conn.execute("SELECT text FROM jd_responsibility WHERE jd_id=%s AND version=%s UNION ALL"
                                  " SELECT text FROM jd_requirement_item WHERE jd_id=%s AND version=%s",
                                  (jd_id, ver, jd_id, ver)):
                allowed.update(m.find_ids(r["text"]))
        out = explainer.explain(item, cv_evidence=cv_evidence, allowed_skills=allowed)
        if row is not None:                      # muc ngoai top N khong co dong rerank_result -> khong cache DB
            conn.execute("UPDATE rerank_result SET explanation_json = %s WHERE run_id = %s AND item_id = %s",
                         (Jsonb(out), run_id, item_id))
        return out
