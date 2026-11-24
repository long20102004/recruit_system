"""B1: schema JD JSON (dau ra Module 1; ten truong gia dinh theo thiet ke 05, doi o `adapter_jd`).

Toi thieu: `jd_id`, `title` va it nhat mot trong `skills`, `requirements`, `responsibilities`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

# --------------------------------------------------------------------------- adapter

TOP_LEVEL = {
    "id": "jd_id",
    "job_id": "jd_id",
    "job_title": "title",
    "position": "title",
    "company_description": "company_intro",
    "about_company": "company_intro",
    "required_skills": "skills",
    "skill": "skills",
    "requirement": "requirements",
    "qualifications": "requirements",
    "responsibility": "responsibilities",
    "duties": "responsibilities",
    "job_description": "responsibilities",
    "workplace": "location",
    "work_type": "work_mode",
    "years_experience": "min_years",
    "min_experience": "min_years",
    "max_experience": "max_years",
}
SKILL = {"skill": "name", "skill_name": "name", "is_required": "required", "priority": "importance",
         "level": "importance"}


def adapt_jd(raw: Any) -> Any:
    if not isinstance(raw, dict):
        return raw
    jd: dict[str, Any] = {}
    for k, v in raw.items():
        key = TOP_LEVEL.get(k, k)
        if key in jd and jd[key] not in (None, "", []):
            continue
        jd[key] = v
    if isinstance(jd.get("skills"), list):
        jd["skills"] = [
            {SKILL.get(k, k): v for k, v in s.items()} if isinstance(s, dict) else s for s in jd["skills"]
        ]
    return jd


# --------------------------------------------------------------------------- schema


class _Base(BaseModel):
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)


class JdSkillIn(_Base):
    name: str
    required: bool = True
    importance: str | None = None


def _as_list(v: Any) -> Any:
    if v is None:
        return []
    if isinstance(v, str):  # doan van -> moi dong mot phan tu
        return [x for x in v.splitlines() if x.strip()]
    return v


class JdInput(_Base):
    jd_id: str | int
    title: str
    company_intro: str | None = None
    location: str | None = None
    work_mode: str | None = None
    min_years: float | None = None
    max_years: float | None = None
    level: str | None = None
    role_group: str | None = None
    edu_required: str | None = None
    skills: list[JdSkillIn | str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    status: str | None = None

    _lists = field_validator("skills", "requirements", "responsibilities", "benefits",
                             mode="before")(_as_list)

    @model_validator(mode="after")
    def _enough_to_match(self) -> "JdInput":
        if not (self.skills or self.requirements or self.responsibilities):
            raise ValueError("JD can it nhat mot trong skills, requirements, responsibilities")
        return self


class InvalidJD(Exception):
    def __init__(self, errors: list[dict], jd_id: str | None = None):
        super().__init__(f"JD sai schema: {len(errors)} loi")
        self.errors = errors
        self.jd_id = jd_id


def validate_jd(data: Any) -> JdInput:
    if not isinstance(data, dict):
        raise InvalidJD([{"loc": [], "msg": "JD JSON phai la object", "type": "type_error"}])
    try:
        return JdInput.model_validate(data)
    except ValidationError as e:
        raise InvalidJD([{"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
                         for err in e.errors()], jd_id=str(data.get("jd_id")) if data.get("jd_id") else None) from None
