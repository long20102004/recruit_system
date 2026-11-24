"""`jd_record`: phieu xu ly JD trong RAM (thiet ke 05). B1-B7 dien, B8 ghi mot giao dich.

Ngu canh dung chung voi Luong A (`CvContext`: config, KB, matcher, lookup, mau, segmenter...) - cung
ham chuan hoa, cung ban chup KB (thiet ke 03 "Buc tranh tong the").
"""

from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from cvmatch.ingest.cv.record import CvContext as PrepContext  # noqa: F401 - dung chung

RequirementKind = Literal["years", "degree", "language", "skill_only", "text"]


class JdSkill(BaseModel):
    skill_id: str
    required: bool
    w_imp: float
    group_id: int | None = None
    source: Literal["module1", "requirements"]
    raw_text: str | None = None


class JdMeta(BaseModel):
    location: str | None = None
    work_mode: str | None = None
    min_years: float | None = None
    max_years: float | None = None
    level_rank: int | None = None
    role_group: str | None = None
    edu_required: Literal["none", "it_related", "any_degree"] | None = None


class RequirementItem(BaseModel):
    idx: int
    text: str
    text_raw: str
    kind: RequirementKind


class Responsibility(BaseModel):
    idx: int
    text: str
    text_raw: str
    context_text: str
    is_generic: bool = False


class JdRecord(BaseModel):
    jd_id: str
    version: int = 1
    status: str = "open"
    raw_json: dict[str, Any]
    norm_json: dict[str, Any] | None = None
    query_text: str | None = None
    skills_found: list[JdSkill] = Field(default_factory=list)
    unknown_skills: list[tuple[str, str | None]] = Field(default_factory=list)
    n_skill_items: int = 0                 # so phan tu `skills` cua Module 1 (tinh ti le chua gan ma)
    meta: JdMeta = Field(default_factory=JdMeta)
    requirement_items: list[RequirementItem] = Field(default_factory=list)
    responsibilities: list[Responsibility] = Field(default_factory=list)
    bm25_query_tokens: list[str] = Field(default_factory=list)
    vectors: dict[str, Any] | None = None
    warnings: list[dict] = Field(default_factory=list)
    ontology_version: str | None = None
    pipeline_version: str | None = None


class JdVersionLookup(Protocol):
    def latest(self, jd_id: str) -> tuple[int, dict] | None:
        """-> (version, raw_json) cua phien ban moi nhat, hoac None."""
        ...


class UnchangedJD(Exception):
    """JD gui lai giong het phien ban moi nhat -> khong tao version moi."""

    def __init__(self, jd_id: str, version: int):
        super().__init__(f"JD {jd_id} khong doi (version {version})")
        self.jd_id, self.version = jd_id, version
