"""Hop dong du lieu giua cac tang (thiet ke 07 muc 6, 08 muc 1).

Cac package chi trao doi qua Postgres va cac model nay; khong import cheo nhau.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Direction = Literal["jd_to_cv", "cv_to_jd"]
MatchLevel = Literal["met", "partial", "not_evidenced"]
MissingSide = Literal["jd_side", "cv_side"]
FEATURES = ("A1", "A2", "B4", "B5", "B1", "B2", "B3", "C1")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- Retrieve -> Rerank (C8)


class ViewScores(_Model):
    dense: float | None = None
    bm25: float | None = None
    skill: float | None = None
    resp: float | None = None


class RerankCandidate(_Model):
    cv_id: str                       # chieu cv_to_jd: day la jd_id (item_id)
    rank: int
    s: ViewScores                    # diem goc s_*
    n: ViewScores                    # diem da min-max n_*
    fused: float


class RerankRequest(_Model):
    direction: Direction
    run_id: str                      # run_id cua lan rerank se tao
    retrieve_run_id: str
    jd_id: str
    jd_version: int
    N: int = 30
    config_version: str              # rerank_config_version
    bertscore_config: str
    candidates: list[RerankCandidate]  # ~200


# --------------------------------------------------------------------------- RR3: FeatureRow


class Features(_Model):
    A1: float | None = None
    A2: float | None = None
    B4: float | None = None
    B5: float | None = None
    B1: float | None = None
    B2: float | None = None
    B3: float | None = None
    C1: float | None = None


class SentenceDetail(_Model):
    """Chi tiet mot cau JD (trach nhiem cho B4, yeu cau dang chu cho B5)."""

    resp_idx: int
    c_j: float
    R_best: float
    bullet_id: int | None
    level: MatchLevel
    matched_words: list[str] = Field(default_factory=list)
    missing_words: list[str] = Field(default_factory=list)
    bullet_flags: list[str] = Field(default_factory=list)


class FeatureRow(_Model):
    cv_id: str
    features: Features
    missing: dict[str, MissingSide] = Field(default_factory=dict)
    resp_detail: list[SentenceDetail] = Field(default_factory=list)
    req_detail: list[SentenceDetail] = Field(default_factory=list)
    s_raw: float
    gate_cap: Literal[100, 70, 50]
    score: int
    flags: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- RR6 -> Explain: FinalItem


class SkillMet(_Model):
    skill: str                       # skill_id
    ev: float
    evidence_id: str                 # bullet_id (dang chuoi) hoac source_field


class SkillPartial(_Model):
    required: str                    # skill_id JD can
    found: str                       # skill_id CV co
    relation: Literal["parent", "child", "sibling"]


class SkillFacts(_Model):
    met: list[SkillMet] = Field(default_factory=list)
    partial: list[SkillPartial] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)   # ky nang bat buoc chua thay


class SentenceFact(_Model):
    resp_id: int
    resp_text: str
    level: MatchLevel
    evidence_id: str | None          # bullet_id
    matched_words: list[str] = Field(default_factory=list)
    missing_words: list[str] = Field(default_factory=list)


class ExperienceFacts(_Model):
    relevant_years: float | None = None
    level_cv: int | None = None
    level_jd: int | None = None
    role_group_cv: str | None = None
    role_group_jd: str | None = None


class Evidence(_Model):
    text_raw: str
    section: str
    item_idx: int
    flags: list[str] = Field(default_factory=list)   # has_negation / is_coursework -> Explain gan nhan


class FinalItem(_Model):
    cv_id: str
    rank: int
    score: int
    score_raw: float
    gate_cap: Literal[100, 70, 50]
    cap_applied: bool
    features: Features
    missing: dict[str, MissingSide] = Field(default_factory=dict)
    skill_facts: SkillFacts = Field(default_factory=SkillFacts)
    resp_facts: list[SentenceFact] = Field(default_factory=list)
    req_facts: list[SentenceFact] = Field(default_factory=list)
    experience_facts: ExperienceFacts = Field(default_factory=ExperienceFacts)
    gaps: list[str] = Field(default_factory=list)
    evidence: dict[str, Evidence] = Field(default_factory=dict)
    flags: list[str] = Field(default_factory=list)
