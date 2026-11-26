"""`cv_record`: phieu xu ly trong RAM (thiet ke 03 muc "`cv_record` la gi").

Moi buoc A1-A10 dien them o; A11 (T05) chep vao Postgres trong mot giao dich.
`CvContext` gom moi thu dung chung (config, KB, matcher, segmenter...) - tao mot lan, dung cho ca lo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Literal, Protocol

import yaml
from pydantic import BaseModel, Field

from cvmatch.core.config import AppConfig
from cvmatch.core.kb.lookup import TitleLookup
from cvmatch.core.kb.matcher import SkillMatcher
from cvmatch.core.kb.snapshot import KBSnapshot
from cvmatch.core.text.normalize import LocationNormalizer, normalize
from cvmatch.core.text.patterns import Patterns
from cvmatch.core.text.segment import Segmenter, make_segmenter

# --------------------------------------------------------------------------- cac o cua phieu


class SkillFound(BaseModel):
    """Mot dong `cv_skill` (A5)."""

    skill_id: str
    ev: float
    source_field: str                       # vd experiences[0].description[1]
    evidence_snippet: str | None
    bullet_ref: tuple[str, int, int] | None = None   # (section, item_idx, pos) -> bullet_id o A11
    last_used: str | None = None


class UnknownSkill(BaseModel):
    text: str
    example: str | None = None


class ExperienceRow(BaseModel):
    """Mot dong `cv_experience` (A6). `idx` = thu tu do moi (0 = moi nhat)."""

    idx: int
    src_index: int                          # vi tri trong mang JSON goc
    section: Literal["experience", "project"]
    kind: Literal["job", "intern", "project_personal", "project_team"]
    title_raw: str | None
    role_group: str | None
    role_group_conf: float | None
    role_group_src: Literal["rule", "keyword"] | None
    start_ym: str | None
    end_ym: str | None
    is_current: bool
    months: int | None
    dates_quality: Literal["ok", "partial", "missing"]


class EducationRow(BaseModel):
    idx: int
    level: str | None
    major_raw: str | None
    major_group: Literal["it", "related", "other"] | None
    status: Literal["graduated", "studying", "unknown"]
    end_year: int | None
    expected_end_ym: str | None


class Meta(BaseModel):
    """`cv_meta` (A6, A7)."""

    location: str | None = None
    years_experience: float | None = None
    intern_months: int | None = None
    level_rank: int | None = None
    level_source: Literal["title", "inferred"] | None = None
    role_group: str | None = None
    major_group: Literal["it", "related", "other"] | None = None
    n_bullets: int = 0


class Bullet(BaseModel):
    """Mot dong `cv_bullet` (A7). `bullet_id` cap o A11."""

    section: Literal["experience", "project"]
    item_idx: int
    pos: int
    text: str
    text_raw: str
    context_text: str
    has_negation: bool = False
    is_coursework: bool = False


class SummarySentence(BaseModel):
    """Mot cau cua `summary` (A7, prep-1.1): ung vien phia CV cua B5 (thiet ke 07 muc 5.4)."""

    idx: int
    text: str
    text_raw: str
    has_negation: bool = False
    is_coursework: bool = False


class Bm25Doc(BaseModel):
    bm25_noacc: list[str]
    bm25_acc: list[str]
    skill_tokens: list[str]


class CvRecord(BaseModel):
    cv_id: str
    ingest_ym: str
    raw_json: dict[str, Any]                # A1: JSON goc (da adapter, ngay da sua ve YYYY-MM)
    flags: list[str] = Field(default_factory=list)
    date_year_only: list[str] = Field(default_factory=list)  # A1: duong dan ngay chi co nam -> dates_quality partial
    content_hash: str | None = None         # A2
    candidate_key: str | None = None
    version: int = 1
    is_latest: bool = True
    replaces_cv_id: str | None = None       # ban cu cung candidate_key (A11 dat is_latest=false)
    anon_json: dict[str, Any] | None = None  # A3 + A4 (da chuan hoa)
    anon_raw: dict[str, Any] | None = None   # A3 + to_raw (giu dau, hoa/thuong) - KHONG ghi DB
    item_order: dict[str, list[int]] = Field(default_factory=dict)  # section -> src_index theo thu tu moi->cu
    skills_found: list[SkillFound] = Field(default_factory=list)    # A5
    unknown_skills: list[UnknownSkill] = Field(default_factory=list)
    meta: Meta = Field(default_factory=Meta)                        # A6
    experiences: list[ExperienceRow] = Field(default_factory=list)
    education: list[EducationRow] = Field(default_factory=list)
    bullets: list[Bullet] = Field(default_factory=list)             # A7
    summary_sentences: list[SummarySentence] = Field(default_factory=list)  # A7 (prep-1.1)
    doc_text: str | None = None                                     # A8
    bm25: Bm25Doc | None = None                                     # A9
    vectors: dict[str, Any] | None = None                           # A10 (T05)
    ontology_version: str | None = None
    pipeline_version: str | None = None

    def add_flag(self, flag: str) -> None:
        if flag not in self.flags:
            self.flags.append(flag)


# --------------------------------------------------------------------------- dung som


class DuplicateCV(Exception):
    """A2: trung hash voi CV da co -> ghi ingest_log status='duplicate' roi dung."""

    def __init__(self, existing_cv_id: str, content_hash: str):
        super().__init__(f"CV trung voi {existing_cv_id}")
        self.existing_cv_id = existing_cv_id
        self.content_hash = content_hash


class DedupLookup(Protocol):
    """Kho tra cuu cho A2. T05 cai tren Postgres (bang `cv`)."""

    def find_by_hash(self, content_hash: str) -> str | None: ...

    def latest_version(self, candidate_key: str) -> tuple[str, int] | None:
        """-> (cv_id, version) cua ban moi nhat cung nguoi, hoac None."""
        ...


class InMemoryDedup:
    """Cai DedupLookup trong RAM (test, nap thu)."""

    def __init__(self) -> None:
        self.by_hash: dict[str, str] = {}
        self.by_key: dict[str, tuple[str, int]] = {}

    def find_by_hash(self, content_hash: str) -> str | None:
        return self.by_hash.get(content_hash)

    def latest_version(self, candidate_key: str) -> tuple[str, int] | None:
        return self.by_key.get(candidate_key)

    def add(self, rec: CvRecord) -> None:
        if rec.content_hash:
            self.by_hash[rec.content_hash] = rec.cv_id
        if rec.candidate_key:
            self.by_key[rec.candidate_key] = (rec.cv_id, rec.version)


# --------------------------------------------------------------------------- ngu canh


@dataclass
class CvContext:
    cfg: AppConfig
    snapshot: KBSnapshot
    matcher: SkillMatcher
    lookup: TitleLookup
    patterns: Patterns
    segmenter: Segmenter
    locations: LocationNormalizer
    role_keywords: dict[str, list[str]]
    hmac_key: bytes
    ingest_ym: str
    dedup: DedupLookup | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        cfg: AppConfig,
        snapshot: KBSnapshot,
        *,
        hmac_key: str | bytes | None = None,
        ingest_ym: str | None = None,
        dedup: DedupLookup | None = None,
        segmenter: Segmenter | None = None,
    ) -> "CvContext":
        key = hmac_key if hmac_key is not None else os.environ.get("CVMATCH_HMAC_KEY")
        if not key:
            raise ValueError("thieu khoa HMAC cho candidate_key (CVMATCH_HMAC_KEY), xem A2")
        matcher = SkillMatcher(snapshot)
        protected = set(cfg.prep.protected_tokens) | matcher.protected_tokens()
        with Path(cfg.pattern_path("role_keywords")).open(encoding="utf-8") as f:
            rk = {g: [normalize(k) for k in kws] for g, kws in (yaml.safe_load(f) or {}).items()}
        return cls(
            cfg=cfg,
            snapshot=snapshot,
            matcher=matcher,
            lookup=TitleLookup(snapshot, fallback=cfg.prep.role_title_fallback),
            patterns=Patterns.from_config(cfg),
            segmenter=segmenter or make_segmenter(cfg.prep.segmenter, protected),
            locations=LocationNormalizer.from_file(cfg.pattern_path("locations")),
            role_keywords=rk,
            hmac_key=key.encode("utf-8") if isinstance(key, str) else key,
            ingest_ym=ingest_ym or date.today().strftime("%Y-%m"),
            dedup=dedup,
        )
