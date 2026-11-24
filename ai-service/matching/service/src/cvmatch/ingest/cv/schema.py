"""A1: schema CV JSON (gia dinh theo thiet ke 04; doi ten truong o `adapter.py`).

- Sai kieu (vd `experiences` khong phai danh sach) -> `InvalidCV`, khong nap tiep.
- Truong tuy chon thieu -> danh sach rong / None.
- Truong la khong co trong schema duoc GIU (extra="allow") trong raw_json, A3 se loc.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class _Base(BaseModel):
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)


def _none_to_list(v: Any) -> Any:
    return [] if v is None else v


class Experience(_Base):
    title: str | None = None
    company: str | None = None
    start: str | int | None = None
    end: str | int | None = None
    is_current: bool | None = None
    description: list[str] | str | None = None
    technologies: list[str] = Field(default_factory=list)
    kind: str | None = None                # job | intern (neu Module 1 co)

    _tech = field_validator("technologies", mode="before")(_none_to_list)


class Project(_Base):
    name: str | None = None
    role: str | None = None
    start: str | int | None = None
    end: str | int | None = None
    is_current: bool | None = None
    description: list[str] | str | None = None
    technologies: list[str] = Field(default_factory=list)
    team_size: int | None = None
    kind: str | None = None                # personal | team (neu Module 1 co)

    _tech = field_validator("technologies", mode="before")(_none_to_list)


class Education(_Base):
    school: str | None = None
    major: str | None = None
    level: str | None = None
    start: str | int | None = None
    end: str | int | None = None
    status: str | None = None              # vd "đang học"


class CvInput(_Base):
    full_name: str | None = None
    email: str | None = None
    phone: str | int | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certificates: list[str | dict] = Field(default_factory=list)
    languages: list[str | dict] = Field(default_factory=list)

    _lists = field_validator("skills", "experiences", "projects", "education", "certificates",
                             "languages", mode="before")(_none_to_list)


class InvalidCV(Exception):
    """CV sai schema (A1): ghi ingest_log status='invalid', khong tao dong `cv`."""

    def __init__(self, errors: list[dict]):
        super().__init__(f"CV sai schema: {len(errors)} loi")
        self.errors = errors


def validate_cv(data: Any) -> CvInput:
    if not isinstance(data, dict):
        raise InvalidCV([{"loc": [], "msg": "CV JSON phai la object", "type": "type_error"}])
    try:
        return CvInput.model_validate(data)
    except ValidationError as e:
        raise InvalidCV([{"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
                         for err in e.errors()]) from None
