"""Doc cau hinh co phien ban (thiet ke 11) va sinh bo khoa phien ban (thiet ke 00 muc 3.4).

Moi tham so (UL) nam trong file YAML o `ai/cvmatch/config/`, khong viet cung trong code.
`active.yaml` chon file nao dang dung cho tung tang.
"""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"

FeatureName = Literal["A1", "A2", "B4", "B5", "B1", "B2", "B3", "C1"]
ViewName = Literal["dense", "bm25", "skill", "resp"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --------------------------------------------------------------------------- prep (11 muc 1.1)


class EvConfig(_Strict):
    in_description: float = 1.0
    in_technologies: float = 0.8
    listed_only: float = 0.6


class WImpConfig(_Strict):
    core: float = 1.0
    medium: float = 0.7
    minor: float = 0.4
    default: float = 1.0


class BulletConfig(_Strict):
    min_words: int = 4


class NoDiacriticsConfig(_Strict):
    threshold: float = 0.05


class JdPrepConfig(_Strict):
    min_query_words: int = 50


class UnknownSkillConfig(_Strict):
    warn_ratio: float = 0.30


class ExperienceConfig(_Strict):
    role_keyword_ratio: float = 2.0


class PatternFiles(_Strict):
    negation: str
    coursework: str
    generic_resp: str
    injection: str
    locations: str
    role_keywords: str


class PrepConfig(_Strict):
    version: str
    doc_template_version: str
    ev: EvConfig
    w_imp: WImpConfig
    bullet: BulletConfig
    no_diacritics: NoDiacriticsConfig
    jd: JdPrepConfig
    unknown_skill: UnknownSkillConfig
    experience: ExperienceConfig
    level_from_years: list[tuple[float, int]]
    protected_tokens: list[str]
    patterns: PatternFiles
    segmenter: Literal["pyvi", "underthesea", "vncorenlp"] = "pyvi"

    @field_validator("level_from_years")
    @classmethod
    def _sorted(cls, v: list[tuple[float, int]]) -> list[tuple[float, int]]:
        if [x[0] for x in v] != sorted(x[0] for x in v):
            raise ValueError("level_from_years phai sap tang theo so nam")
        return v


# --------------------------------------------------------------------------- retrieve (11 muc 1.2)


class Bm25Config(_Strict):
    k1: float = 1.2
    b: float = 0.75
    query_mode: Literal["full_jd", "title_skills"] = "full_jd"
    field: Literal["noacc", "acc"] = "noacc"
    use_skill_tokens: bool = True


class HardFilterConfig(_Strict):
    enabled: bool = False


class ReverseSkillConfig(_Strict):
    min_imp_sum: float = 3.0


class ReverseConfig(_Strict):
    only_open: Literal[True] = True
    K_max: int = 50
    bm25_query_mode: Literal["condensed_cv", "full_cv"] = "condensed_cv"
    skill: ReverseSkillConfig
    min_pool_minmax: int = 10


class RetrieveConfig(_Strict):
    version: str
    K: int = 200
    views_enabled: list[ViewName]
    view_weights: dict[ViewName, float]
    normalization: Literal["minmax", "dbsf"] = "minmax"
    fusion: Literal["score_sum", "rrf"] = "score_sum"
    rrf_k: int = 60
    bm25: Bm25Config
    hard_filters: HardFilterConfig
    min_pool_warn: int = 20
    reverse: ReverseConfig


# --------------------------------------------------------------------------- bertscore (07 muc 2)


class BertScoreConfig(_Strict):
    model: str
    revision: str
    model_short: str
    layer: int = 24
    idf: bool = False
    rescale_baseline: bool = False
    score: Literal["recall", "precision", "f1"] = "recall"
    split: Literal["S1", "S2", "S3"] = "S2"
    max_len: int = 2048
    dtype: Literal["fp32", "fp16"] = "fp32"
    input: Literal["text_raw", "text"] = "text_raw"
    canonicalize_aliases: bool = True
    mask_numbers: bool = True

    def key(self) -> str:
        """Khoa `bertscore_config` (thiet ke 00 muc 3.4, 07 muc 2).

        Mau trong thiet ke: `bge-m3@5617a9f61b/L24/noidf/norescale/2048/mask1`.
        Bo sung them co doi alias, dau vao va kieu so vi ca ba deu doi embedding/diem
        nen phai nam trong khoa cache.
        """
        parts = [
            f"{self.model_short}@{self.revision[:10]}",
            f"L{self.layer}",
            "idf" if self.idf else "noidf",
            "rescale" if self.rescale_baseline else "norescale",
            str(self.max_len),
            f"mask{int(self.mask_numbers)}",
            f"alias{int(self.canonicalize_aliases)}",
            self.input,
            self.dtype,
        ]
        return "/".join(parts)


# --------------------------------------------------------------------------- rerank (11 muc 1.3)


class A1Config(_Strict):
    use_kb_rel: bool = False


class CalibConfig(_Strict):
    lo: float = 0.65
    hi: float = 0.90

    @model_validator(mode="after")
    def _order(self) -> "CalibConfig":
        if not self.lo < self.hi:
            raise ValueError("b4.calib: can lo < hi")
        return self


class LevelThresholds(_Strict):
    met: float = 0.6
    partial: float = 0.3


class B4Config(_Strict):
    calib: CalibConfig
    level: LevelThresholds
    m_negation: float = 0.3
    m_coursework: float = 0.6
    generic_weight: float = 0.0


class AlignConfig(_Strict):
    word_sim_min: float = 0.75
    literal_match: bool = False      # tu xuat hien nguyen van trong gach -> khop (T12)


class RelConfig(_Strict):
    same: float = 1.0
    parent_child: float = 0.7
    sibling: float = 0.4


class B1Config(_Strict):
    recent_months: int = 36
    recent_boost: float = 2.0


class B2Config(_Strict):
    project_personal_weight: float = 0.3
    overqual_penalty: bool = True
    overqual_penalty_reverse: bool = False


class GateConfig(_Strict):
    thresholds: tuple[float, float] = (0.5, 0.7)
    caps: tuple[int, int] = (50, 70)


class MissingConfig(_Strict):
    cv_side_policy: Literal["pool_median", "drop", "zero"] = "pool_median"


class LowDataQualityConfig(_Strict):
    min_missing: int = 3


class ScoreConfig(_Strict):
    bands: tuple[int, int] = (80, 60)


class Rr5Config(_Strict):
    enabled: bool = False


class CacheConfig(_Strict):
    token_lru_gb: float = 20


class RerankConfig(_Strict):
    version: str
    N: int = 30
    reverse_N: int = 10
    features_enabled: list[FeatureName]
    weights: dict[FeatureName, float]
    a1: A1Config
    b4: B4Config
    align: AlignConfig
    rel: RelConfig
    b1: B1Config
    b2: B2Config
    gate: GateConfig
    missing: MissingConfig
    low_data_quality: LowDataQualityConfig
    score: ScoreConfig
    rr5: Rr5Config
    cache: CacheConfig

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> "RerankConfig":
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-9:  # Q7: tong trong so prior = 1,00
            raise ValueError(f"rerank.weights phai cong = 1.00 (hien {total:.4f})")
        missing = set(self.features_enabled) - set(self.weights)
        if missing:
            raise ValueError(f"feature bat nhung thieu trong so: {sorted(missing)}")
        return self


# --------------------------------------------------------------------------- explain (11 muc 1.4)


class BandLabels(_Strict):
    high: str
    mid: str
    low: str


class ExplainConfig(_Strict):
    version: str
    mode: Literal["template", "llm"] = "template"
    lazy: bool = True
    template_version: str
    max_questions: int = 3
    band_labels: BandLabels
    template_file: str = "templates/explain-tpl-1.0.j2"     # tuong doi thu muc config
    forbidden_file: str = "patterns/explain_forbidden.txt"  # tu nhay cam / loi khuyen tuyen-loai (EX4)
    max_examples: int = 3                                   # so trach nhiem vi du o "Diem manh"


# --------------------------------------------------------------------------- models


class EmbedConfig(_Strict):
    model: str
    revision: str
    key: str
    dim: int = 1024
    device: Literal["cuda", "cpu"] = "cuda"
    dtype: Literal["fp32", "fp16"] = "fp32"
    batch_size: int = 16
    max_len: int = 8192


class ModelsConfig(_Strict):
    embed: EmbedConfig


# --------------------------------------------------------------------------- tong hop


class Versions(_Strict):
    """Bo khoa phien ban ghi vao moi ban ghi (thiet ke 00 muc 3.4)."""

    ontology_version: str | None
    pipeline_version: str
    embed_model: str
    bertscore_config: str
    rerank_config_version: str


class AppConfig(_Strict):
    config_dir: Path
    files: dict[str, str] = Field(description="ten file da nap cho tung tang")
    ontology_version: str | None
    prep: PrepConfig
    retrieve: RetrieveConfig
    rerank: RerankConfig
    bertscore: BertScoreConfig
    explain: ExplainConfig
    models: ModelsConfig

    @property
    def versions(self) -> Versions:
        return Versions(
            ontology_version=self.ontology_version,
            pipeline_version=self.prep.version,
            embed_model=self.models.embed.key,
            bertscore_config=self.bertscore.key(),
            rerank_config_version=self.rerank.version,
        )

    def pattern_path(self, name: str) -> Path:
        return self.config_dir / getattr(self.prep.patterns, name)

    def to_json_dict(self) -> dict:
        """Ban dump on dinh de ghi vao match_run.config_json / rerank_run.config_json."""
        d = self.model_dump(mode="json", exclude={"config_dir"})
        return d

    def config_hash(self) -> str:
        return config_hash(self.to_json_dict())


def config_hash(obj: dict) -> str:
    canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _read_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: noi dung YAML phai la mapping")
    return data


def load_config(config_dir: str | Path | None = None, overrides: dict | None = None) -> AppConfig:
    """Nap cau hinh tu `active.yaml`.

    `overrides`: dict long nhau ghi de len gia tri da nap (dung cho ablation, vd
    `{"rerank": {"b4": {"calib": {"lo": 0.6}}}}`).
    Bien moi truong: CVMATCH_CONFIG_DIR (thu muc), CVMATCH_DEVICE (ghi de models.embed.device).
    """
    cdir = Path(config_dir or os.environ.get("CVMATCH_CONFIG_DIR") or DEFAULT_CONFIG_DIR)
    active = _read_yaml(cdir / "active.yaml")
    sections = ["prep", "retrieve", "rerank", "bertscore", "explain", "models"]
    raw: dict = {s: _read_yaml(cdir / active[s]) for s in sections}

    device = os.environ.get("CVMATCH_DEVICE")
    if device:
        raw["models"].setdefault("embed", {})["device"] = device
    if overrides:
        raw = _deep_merge(raw, overrides)

    return AppConfig(
        config_dir=cdir,
        files={s: active[s] for s in sections},
        ontology_version=(overrides or {}).get("ontology_version", active.get("ontology_version")),
        **{s: raw[s] for s in sections},
    )


def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Cau hinh mac dinh cua tien trinh (nap mot lan)."""
    return load_config()
