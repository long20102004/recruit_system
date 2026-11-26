"""S03, S04 (prep-1.2): sua du lieu vao — V-02, V-05, V-06, V-07, V-18. Khong DB, khong GPU."""

import copy
import json
from pathlib import Path

import pytest

from cvmatch.core.config import load_config
from cvmatch.core.kb.snapshot import KBSnapshot
from cvmatch.ingest.cv.adapter import adapt_cv
from cvmatch.ingest.cv.pipeline import build_cv_record
from cvmatch.ingest.cv.record import CvContext
from cvmatch.ingest.jd.pipeline import build_jd_record

FIX = Path(__file__).resolve().parents[1] / "fixtures"
KB = Path(__file__).resolve().parents[3] / "kb-builder" / "out" / "snapshot" / "kb-2026-11-24"

OLD = {"prep": {"experience": {"null_end_current": "all"}, "education": None, "role_title_fallback": False,
                "jd": {"split_min_words": None}}}
NEW = {"prep": {"experience": {"null_end_current": "latest"},
                "education": {"max_study_years": 5, "default_duration_years": 4},
                "role_title_fallback": True, "jd": {"split_min_words": 25}}}


def ctx_of(over, snap):
    return CvContext.create(load_config(overrides=over), snap, hmac_key="k", ingest_ym="2026-11")


@pytest.fixture(scope="module")
def snap():
    if not (KB / "manifest.json").exists():
        pytest.skip(f"khong co snapshot {KB}")
    return KBSnapshot.from_dir(KB)


# ------------------------------------------------------------------ V-06


def _two_open_jobs():
    return {"personal_info": {"email": "a@example.test"},
            "experience": [{"job_title": "Java Developer", "start_date": "03/2023", "end_date": None,
                            "description": ["Phát triển REST API bằng Spring Boot cho hệ thống bán hàng"]},
                           {"job_title": "Java Developer", "start_date": "01/2019", "end_date": None,
                            "description": ["Viết module quản lý kho bằng Java và MySQL"]}]}


def test_v06_adapter_only_latest_is_current():
    old = adapt_cv(_two_open_jobs())
    assert [e.get("is_current") for e in old["experiences"]] == [True, True]
    new = adapt_cv(_two_open_jobs(), null_end_current="latest")
    assert [e.get("is_current") for e in new["experiences"]] == [True, None]


def test_v06_years_not_counted_twice(snap):
    old = build_cv_record(_two_open_jobs(), ctx_of(OLD, snap))
    new = build_cv_record(_two_open_jobs(), ctx_of(NEW, snap))
    assert old.meta.years_experience == pytest.approx(7.8)       # 2019-01 .. hien tai (gop chong lan, quy uoc dem thang)
    assert new.meta.years_experience == pytest.approx(3.7)       # chi 2023-03 .. 2026-11
    assert "years_uncertain" in new.flags


# ------------------------------------------------------------------ V-07


def _student(start, end=None):
    return {"personal_info": {"email": "s@example.test"},
            "education": [{"school": "X", "major": "Công nghệ thông tin", "start_year": start, "end_year": end}],
            "skills": ["Java"]}


def test_v07_recent_start_without_end_is_studying(snap):
    assert build_cv_record(_student(2023), ctx_of(OLD, snap)).education[0].status == "unknown"
    r = build_cv_record(_student(2023), ctx_of(NEW, snap))
    assert r.education[0].status == "studying" and r.education[0].expected_end_ym == "2027-01"
    assert "edu_end_inferred" in r.flags


def test_v07_old_start_stays_unknown(snap):
    r = build_cv_record(_student(2015), ctx_of(NEW, snap))
    assert r.education[0].status == "unknown" and "edu_end_inferred" not in r.flags


# ------------------------------------------------------------------ V-02


def _jd(title, **kw):
    d = {"jd_id": "J-" + title, "title": title, "skills": [{"name": "Java", "required": True}],
         "responsibilities": ["Phát triển REST API bằng Spring Boot cho hệ thống thanh toán"]}
    d.update(kw)
    return d


@pytest.mark.parametrize("title", ["Java Intern", "Thực tập sinh Java", "Fresher Java", "Backend Intern"])
def test_v02_title_with_level_gets_role(snap, title):
    assert build_jd_record(_jd(title), ctx_of(OLD, snap)).meta.role_group is None
    assert build_jd_record(_jd(title), ctx_of(NEW, snap)).meta.role_group == "Backend"


def test_v02_bare_level_word_has_no_role(snap):
    assert build_jd_record(_jd("Intern"), ctx_of(NEW, snap)).meta.role_group is None


# ------------------------------------------------------------------ V-05, V-18

PARA = ("Thiết kế và phát triển REST API cho hệ thống thanh toán bằng Spring Boot. Tối ưu truy vấn PostgreSQL cho "
        "các báo cáo doanh thu hằng ngày. Viết unit test và tham gia review code với các thành viên khác. "
        "Phối hợp với nhóm frontend để tích hợp giao diện quản trị.")


def test_v05_long_paragraph_is_split(snap):
    old = build_jd_record(_jd("Java Developer", responsibilities=[PARA]), ctx_of(OLD, snap))
    new = build_jd_record(_jd("Java Developer", responsibilities=[PARA]), ctx_of(NEW, snap))
    assert len(old.responsibilities) == 1 and len(new.responsibilities) == 4


def test_v05_list_unchanged(snap):
    lines = ["Thiết kế REST API cho hệ thống thanh toán", "Tối ưu truy vấn PostgreSQL cho báo cáo"]
    assert len(build_jd_record(_jd("Java Developer", responsibilities=lines), ctx_of(NEW, snap)).responsibilities) == 2


def test_v18_warnings_have_hint(snap):
    rec = build_jd_record(_jd("Java Developer"), ctx_of(NEW, snap))
    short = next(w for w in rec.warnings if w["code"] == "short_query")
    assert short["hint"] and "trách nhiệm" in short["hint"]
