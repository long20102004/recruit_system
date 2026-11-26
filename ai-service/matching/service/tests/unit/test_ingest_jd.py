"""T06: Luong B. Test vang = JD mau thiet ke 05."""

import copy
import json
from pathlib import Path

import pytest

from cvmatch.core.config import load_config
from cvmatch.ingest.cv.record import CvContext
from cvmatch.ingest.jd.requirements import parse_years
from cvmatch.ingest.jd.pipeline import build_jd_record
from cvmatch.ingest.jd.record import UnchangedJD
from cvmatch.ingest.jd.schema import InvalidJD

FIX = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE = json.loads((FIX / "jd" / "jd_sample.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ctx(kb_mini):
    return CvContext.create(load_config(), kb_mini, hmac_key="x")


@pytest.fixture(scope="module")
def rec(ctx):
    return build_jd_record(copy.deepcopy(SAMPLE), ctx)


def jd_with(**kw):
    d = copy.deepcopy(SAMPLE)
    d.update(kw)
    return d


def test_b01_b02(rec):
    assert (rec.jd_id, rec.version, rec.status) == ("JD-0412", 1, "open")
    assert rec.raw_json["title"] == "Senior Backend Developer (Java)"
    assert rec.norm_json["title"] == "senior backend developer (java)"
    assert rec.norm_json["location"] == "ho_chi_minh" and rec.norm_json["work_mode"] == "hybrid"


def test_b03_query_text(rec):
    assert rec.query_text == (
        "Chức danh: senior backend developer (java)\n"
        "Kỹ năng: java, spring boot, postgresql, kafka\n"
        "Yêu cầu: tối thiểu 4 năm kinh nghiệm backend. hiểu biết về microservices\n"
        "Trách nhiệm: thiết kế và phát triển api cho hệ thống thanh toán. tối ưu hiệu năng truy vấn cơ sở dữ liệu."
        " tham gia các buổi họp của team"
    )
    assert "fintech" not in rec.query_text and "lương" not in rec.query_text


def test_b04_jd_skill(rec):
    got = {s.skill_id: (s.required, s.w_imp, s.source) for s in rec.skills_found}
    assert got == {
        "S0001": (True, 1.0, "module1"),        # Java
        "S0002": (True, 1.0, "module1"),        # Spring Boot
        "S0015": (True, 0.7, "module1"),        # PostgreSQL
        "S0021": (False, 0.4, "module1"),       # Kafka
        "S0023": (False, 0.4, "requirements"),  # Microservices tim them
    }
    assert all(s.group_id is None for s in rec.skills_found)


def test_b05_meta_and_requirement_kinds(rec):
    m = rec.meta
    assert (m.location, m.work_mode, m.min_years, m.max_years, m.level_rank, m.role_group, m.edu_required) == \
        ("ho_chi_minh", "hybrid", 4, None, 4, "Backend", None)
    assert [(r.idx, r.text_raw, r.kind) for r in rec.requirement_items] == [
        (0, "Tối thiểu 4 năm kinh nghiệm backend", "years"),
        (1, "Hiểu biết về microservices", "text"),
    ]


def test_b06_responsibilities(rec):
    assert [(r.idx, r.text, r.is_generic) for r in rec.responsibilities] == [
        (0, "thiết kế và phát triển api cho hệ thống thanh toán", False),
        (1, "tối ưu hiệu năng truy vấn cơ sở dữ liệu", False),
        (2, "tham gia các buổi họp của team", True),
    ]
    assert rec.responsibilities[0].text_raw == "Thiết kế và phát triển API cho hệ thống thanh toán"
    assert rec.responsibilities[0].context_text.startswith("senior backend developer (java): ")


def test_b07_tokens(rec):
    t = rec.bm25_query_tokens
    assert "thanh_toan" in t and "thiet_ke" in t and "spring" in t
    assert t[-5:] == ["skill_s0001", "skill_s0002", "skill_s0015", "skill_s0021", "skill_s0023"]
    assert "chuc_danh" not in t


def test_b08_no_warnings(rec):
    assert rec.warnings == []


# ------------------------------------------------------------------ cac truong hop khac


def test_or_groups(ctx):
    r = build_jd_record(jd_with(skills=[{"name": "MySQL/PostgreSQL"}, "Java hoặc Kotlin", "Docker"]), ctx)
    g = {s.skill_id: s.group_id for s in r.skills_found}
    assert g["S0016"] == g["S0015"] is not None          # MySQL / PostgreSQL
    assert g["S0001"] == g["S0030"] is not None          # Java hoac Kotlin
    assert g["S0016"] != g["S0001"] and g["S0019"] is None


@pytest.mark.parametrize("line,kind", [
    ("Tốt nghiệp ĐH chuyên ngành CNTT", "degree"),
    ("Đọc hiểu tài liệu tiếng Anh", "language"),
    ("Thành thạo Java và Spring Boot", "skill_only"),
    ("Có kinh nghiệm thiết kế hệ thống chịu tải cao", "text"),
    ("Ít nhất 2 năm kinh nghiệm làm việc với React", "years"),
    ("IELTS 6.5 trở lên", "language"),
])
def test_requirement_kinds(ctx, line, kind):
    r = build_jd_record(jd_with(requirements=[line]), ctx)
    assert r.requirement_items[0].kind == kind


def test_edu_required(ctx):
    r = build_jd_record(jd_with(requirements=["Tốt nghiệp ĐH chuyên ngành CNTT hoặc liên quan"]), ctx)
    assert r.meta.edu_required == "it_related"
    r2 = build_jd_record(jd_with(requirements=["Tốt nghiệp đại học"]), ctx)
    assert r2.meta.edu_required == "any_degree"


@pytest.mark.parametrize("text,expected", [
    ("Tối thiểu 4 năm kinh nghiệm backend", (4, None)), ("3–5 năm kinh nghiệm", (3, 5)),
    ("Từ 2 đến 4 năm kinh nghiệm", (2, 4)), ("2+ years of experience", (2, None)),
    ("At least 3 years", (3, None)), ("Có kinh nghiệm backend", (None, None)),
])
def test_parse_years(text, expected):
    assert parse_years(text) == expected


def test_min_years_from_requirements(ctx):
    d = jd_with(requirements=["3-5 năm kinh nghiệm phát triển phần mềm"])
    d.pop("min_years")
    r = build_jd_record(d, ctx)
    assert (r.meta.min_years, r.meta.max_years) == (3, 5)


def test_invalid(ctx):
    with pytest.raises(InvalidJD):
        build_jd_record({"jd_id": "X", "title": "Dev"}, ctx)           # khong co skills/req/resp
    with pytest.raises(InvalidJD):
        build_jd_record({"jd_id": "X", "skills": ["Java"]}, ctx)       # thieu title


def test_warnings(ctx):
    r = build_jd_record({"jd_id": "J2", "title": "Dev", "skills": [{"name": "Figma", "required": True}],
                         "responsibilities": ["Tham gia các buổi họp của team"]}, ctx)
    codes = {w["code"] for w in r.warnings}
    assert codes == {"no_required_skill", "no_responsibility", "short_query", "many_unmapped_skills"}
    assert r.unknown_skills == [("figma", "jd skills: Figma")]


def test_versioning_and_unchanged(ctx):
    class V:
        def __init__(self, data):
            self.data = data

        def latest(self, jd_id):
            return (3, self.data)

    base = build_jd_record(copy.deepcopy(SAMPLE), ctx)
    with pytest.raises(UnchangedJD):
        build_jd_record(copy.deepcopy(SAMPLE), ctx, V(base.raw_json))
    r = build_jd_record(jd_with(min_years=5), ctx, V(base.raw_json))
    assert r.version == 4


def test_paragraph_fields_and_status_alias(ctx):
    r = build_jd_record(jd_with(responsibilities="Thiết kế API thanh toán cho đối tác\nTối ưu truy vấn cơ sở dữ liệu",
                                status="Đang tuyển"), ctx)
    assert len(r.responsibilities) == 2 and r.status == "open"
