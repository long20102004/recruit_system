"""Request / response cua API (pydantic -> OpenAPI cho phia Java, xem `/openapi.json`)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

JdStatus = Literal["open", "draft", "closed", "expired"]
View = Literal["dense", "bm25", "skill", "resp"]


class _Out(BaseModel):
    model_config = ConfigDict(extra="allow")


class CvIngestResult(_Out):
    source: str | None = None
    status: Literal["ok", "duplicate", "invalid", "failed"]
    cv_id: str | None = Field(None, description="ok: cv_id moi; duplicate: cv_id da co")
    version: int | None = None
    flags: list[str] = Field(default_factory=list, description="vd low_content, no_diacritics, date_unparsed")
    detail: dict[str, Any] = Field(default_factory=dict, description="invalid: errors; failed: error")


class CvBatchIn(BaseModel):
    items: list[dict[str, Any]] = Field(..., min_length=1, description="cac CV JSON (dau ra Module 1)")
    background: bool = Field(True, description="true -> tra job_id, xem GET /jobs/{id}")


class CvBatchOut(BaseModel):
    results: list[CvIngestResult]


class CvDeleteOut(BaseModel):
    cv_id: str
    deleted: bool


class JdIngestResult(_Out):
    source: str | None = None
    status: Literal["ok", "unchanged", "invalid", "failed"]
    jd_id: str | None = None
    version: int | None = None
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    detail: dict[str, Any] = Field(default_factory=dict)


class JdStatusIn(BaseModel):
    status: JdStatus


class JdStatusOut(BaseModel):
    jd_id: str
    version: int
    status: JdStatus


class HardFilters(BaseModel):
    location: str | None = Field(None, description="vd 'TP.HCM'; CV thieu dia diem duoc cho qua")
    min_years: float | None = Field(None, ge=0)
    allow_remote: bool = True


class MatchIn(BaseModel):
    K: int | None = Field(None, ge=1, le=5000, description="so CV Retrieve giu lai (mac dinh retrieve.K)")
    N: int | None = Field(None, ge=1, le=500, description="so CV tra ve sau Rerank (mac dinh rerank.N)")
    hard_filters: HardFilters | None = None
    exclude_cv_ids: list[str] = Field(default_factory=list, description="vd CV da phong van")
    include_cv_ids: list[str] | None = Field(
        None, description="chi xet cac CV nay (vd ung vien da nop don); null = ca kho. Diem phu thuoc pool "
                          "(chuan hoa min-max, pool_median) nen pool nho cho diem khac pool lon")
    views: list[View] | None = Field(None, description="mac dinh retrieve.views_enabled")
    ref_ym: str | None = Field(None, pattern=r"^\d{4}-\d{2}$", description="thang tham chieu B1 (mac dinh thang nay)")
    background: bool = False


class SkillSummary(BaseModel):
    met: list[str] = Field(default_factory=list, description="ky nang JD can, CV co")
    partial: list[str] = Field(default_factory=list, description="ky nang JD can, CV co ky nang gan (cha/con/anh em)")
    missing: list[str] = Field(default_factory=list, description="ky nang bat buoc chua thay trong CV")


class ItemDetail(BaseModel):
    features: dict[str, float | None] = Field(
        default_factory=dict, description="A1, A2, B1-B5, C1 trong [0,1]; null = tat hoac thieu du lieu")
    skills: SkillSummary = Field(default_factory=SkillSummary)


class MatchItem(ItemDetail):
    cv_id: str
    rank: int
    score: int = Field(..., ge=0, le=100)
    band: Literal["high", "mid", "low"]
    cap_applied: bool
    flags: list[str]


class MatchOut(BaseModel):
    run_id: str = Field(..., description="rerank run - dung cho GET /match/{run_id}/cv/{cv_id}/explain")
    retrieve_run_id: str
    jd_id: str
    jd_version: int
    n_pool: int
    items: list[MatchItem]
    warnings: list[dict[str, Any]]
    timings: dict[str, float]


class ReverseFilters(BaseModel):
    location: str | None = Field(None, description="JD khac dia diem (va khong remote) bi loai; JD thieu -> cho qua")
    work_mode: str | None = None


class MatchCvIn(BaseModel):
    K: int | None = Field(None, ge=1, le=500, description="mac dinh min(reverse.K_max, so JD mo)")
    N: int | None = Field(None, ge=1, le=100, description="mac dinh rerank.reverse_N (10)")
    hard_filters: ReverseFilters | None = None
    exclude_jd_ids: list[str] = Field(default_factory=list)
    include_jd_ids: list[str] | None = Field(None, description="chi xet cac JD nay; null = moi JD dang mo")
    views: list[View] | None = None
    ref_ym: str | None = Field(None, pattern=r"^\d{4}-\d{2}$")
    background: bool = False


class MatchCvItem(ItemDetail):
    jd_id: str
    jd_version: int
    rank: int
    score: int = Field(..., ge=0, le=100)
    band: Literal["high", "mid", "low"]
    cap_applied: bool
    flags: list[str]


class MatchCvOut(BaseModel):
    run_id: str = Field(..., description="rerank run - dung cho GET /match/{run_id}/jd/{jd_id}/explain")
    retrieve_run_id: str
    cv_id: str
    n_pool: int
    items: list[MatchCvItem]
    warnings: list[dict[str, Any]]
    timings: dict[str, float]


class PreviewIn(BaseModel):
    cv: dict[str, Any] = Field(..., description="CV JSON tam: KHONG luu lai sau khi tra ket qua")
    N: int | None = Field(None, ge=1, le=100)
    hard_filters: ReverseFilters | None = None
    ref_ym: str | None = Field(None, pattern=r"^\d{4}-\d{2}$")
    n_explain: int | None = Field(None, ge=0, le=100, description="so JD kem giai thich (mac dinh: tat ca)")


class PreviewExplain(BaseModel):
    jd_id: str
    band: str
    band_label: str
    text: str


class PreviewOut(BaseModel):
    status: str
    items: list[MatchCvItem] = Field(default_factory=list)
    explanations: list[PreviewExplain] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    detail: dict[str, Any] = Field(default_factory=dict)


class ExplainOut(_Out):
    mode: str
    template_version: str
    cv_id: str
    score: int
    band: str
    band_label: str
    cap_applied: bool
    text: str
    sections: dict[str, Any]
    cache_key: str


class JobOut(BaseModel):
    job_id: str
    kind: str
    status: Literal["queued", "running", "done", "failed"]
    created_at: str
    finished_at: str | None = None
    result: Any = None
    error: str | None = None


class HealthOut(_Out):
    status: str = Field(..., description="ok | degraded (DB loi -> HTTP 503)")
    db: str = "ok"
    versions: dict[str, str | None]
    config_files: dict[str, str]
    config_hash: str
    encoder: str
    n_cv: int
    n_jd_open: int = 0
    index_memory_mb: dict[str, float]


class ErrorOut(BaseModel):
    detail: str
