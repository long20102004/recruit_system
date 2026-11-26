"""I03: dau ra THAT cua Module 1 (`ai-service/extraction`) qua adapter + Luong A (A1-A9), khong DB.

Fixture la du lieu gia dung hinh dang Module 1 (`tests/fixtures/module1/make_fixtures.py`).
"""

import copy
import json
from pathlib import Path

import pytest

from cvmatch.core.config import load_config
from cvmatch.core.kb.snapshot import KBSnapshot
from cvmatch.ingest.cv.adapter import KG_FIELDS, adapt_cv
from cvmatch.ingest.cv.pipeline import build_cv_record
from cvmatch.ingest.cv.record import CvContext
from cvmatch.ingest.cv.schema import validate_cv

M1 = Path(__file__).resolve().parents[1] / "fixtures" / "module1"
KB = Path(__file__).resolve().parents[3] / "kb-builder" / "out" / "snapshot" / "kb-2026-11-24"


def load(name: str) -> dict:
    return json.loads((M1 / f"{name}.json").read_text(encoding="utf-8"))


ALL = sorted(p.stem for p in M1.glob("m1_*.json"))


@pytest.mark.parametrize("name", ALL)
def test_fixture_validates_and_keeps_sections(name):
    raw = load(name)
    cv = validate_cv(adapt_cv(copy.deepcopy(raw)))
    raw = raw.get("data", raw)                                # fixture co vo {message, code, data}
    assert len(cv.experiences) == len(raw["experience"])
    assert len(cv.projects) == len(raw["personal_projects"])
    assert len(cv.education) == len(raw["education"])
    assert cv.summary == raw["objective"]
    assert cv.email == raw["personal_info"]["email"] and cv.full_name == raw["personal_info"]["full_name"]


def test_adapter_lifts_personal_info_and_drops_kg():
    raw = load("m1_backend_java")
    cv = adapt_cv(copy.deepcopy(raw))
    assert "personal_info" not in cv and cv["phone"] == "0900000001" and cv["github_url"].startswith("https://")
    assert not set(KG_FIELDS) & set(cv)                       # JVM (implied) khong thanh ky nang
    assert cv["projects"][0]["technologies"] == ["Java", "Spring Boot", "Redis", "MySQL"]
    assert (cv["education"][0]["start"], cv["education"][0]["end"]) == ("2015", "2019")
    assert cv["experiences"][0]["is_current"] is True        # end_date = null -> dang lam
    assert "is_current" not in cv["experiences"][1]


def test_root_values_win_over_personal_info():
    cv = adapt_cv({"email": "acct@example.test", "personal_info": {"email": "cv@example.test", "full_name": "X"}})
    assert cv["email"] == "acct@example.test" and cv["full_name"] == "X"


def test_null_end_without_start_is_not_current():
    cv = adapt_cv({"experience": [{"job_title": "Tester", "start_date": None, "end_date": None}]})
    assert "is_current" not in cv["experiences"][0]


@pytest.fixture(scope="module")
def ctx():
    if not (KB / "manifest.json").exists():
        pytest.skip(f"khong co snapshot {KB}")
    return CvContext.create(load_config(), KBSnapshot.from_dir(KB), hmac_key="k", ingest_ym="2026-11")


def test_luong_a_on_module1(ctx):
    def rec(name):
        return build_cv_record(load(name), ctx)

    be = rec("m1_backend_java")
    assert be.flags == [] and be.candidate_key
    assert be.meta.years_experience == 7.3                    # 2019-07 .. 2022-02 + 2022-03 .. hien tai (2026-11)
    snap = KBSnapshot.from_dir(KB)
    names = {snap.skills[s.skill_id].name for s in be.skills_found}
    assert {"Java", "Spring Boot", "PostgreSQL", "Hibernate", "Redis"} <= names
    assert "JVM" not in names                                 # implied_skills cua KG bi bo

    fe = rec("m1_frontend_english")
    assert fe.flags == [] and fe.meta.years_experience == 4.7    # "Present"

    st = rec("m1_student_phone_only")
    assert st.candidate_key and "no_identity" not in st.flags    # chi co sdt van nhan dang duoc

    assert "no_identity" in rec("m1_empty_personal").flags
    assert {"date_unparsed", "years_uncertain"} <= set(rec("m1_devops_bad_date").flags)


def test_same_account_email_is_same_candidate(ctx):
    a = load("m1_backend_java")
    b = copy.deepcopy(a)
    b["personal_info"]["email"] = " GIA.backend@Example.test"
    b["skills"].append("Kafka")
    ra, rb = build_cv_record(a, ctx), build_cv_record(b, ctx)
    assert ra.candidate_key == rb.candidate_key and ra.content_hash != rb.content_hash


# ------------------------------------------------ vo ApiResponse cua backend {message, code, data}
# hinh dang: data/demo/cv/cv_parse_demo.json (fixture thay PII bang du lieu gia)

ENV = "m1_envelope_backend_intern"


def test_envelope_is_unwrapped():
    raw = load(ENV)
    cv = adapt_cv(copy.deepcopy(raw))
    assert not {"message", "code", "data"} & set(cv)
    assert cv["email"] == raw["data"]["personal_info"]["email"]
    assert len(cv["experiences"]) == 1 and len(cv["projects"]) == 2
    assert cv["summary"] == raw["data"]["objective"]


def test_envelope_without_cv_is_invalid():
    from cvmatch.ingest.cv.adapter import unwrap_envelope
    from cvmatch.ingest.cv.schema import InvalidCV
    assert unwrap_envelope({"message": "Parse failed", "code": 500, "data": None}) is None
    with pytest.raises(InvalidCV):
        validate_cv(adapt_cv({"message": "Parse failed", "code": 500, "data": None}))


def test_cv_with_data_field_is_not_unwrapped():
    cv = adapt_cv({"full_name": "X", "data": {"skills": ["Java"]}})   # khong phai vo: co khoa CV
    assert cv["full_name"] == "X" and "data" in cv


def test_luong_a_on_envelope(ctx):
    raw = load(ENV)
    r = build_cv_record(raw, ctx)
    assert r.flags == [] and r.candidate_key
    # hash tinh tren CV ben trong: doi message/code cua vo khong sinh CV moi
    other = copy.deepcopy(raw)
    other["message"] = "OK"
    assert build_cv_record(other, ctx).content_hash == r.content_hash == build_cv_record(raw["data"], ctx).content_hash
    assert r.meta.role_group == "Backend" and r.meta.major_group == "it"
    assert r.experiences[0].start_ym == "2025-10" and r.experiences[0].end_ym == "2026-05"  # "October 2025"
    assert r.education[0].status == "studying" and r.education[0].end_year == 2027
    names = {ctx.snapshot.skills[s.skill_id].name for s in r.skills_found}
    assert {"Java", "Spring Boot", "MySQL", "PostgreSQL", "Redis", "Docker"} <= names
    assert "github_url" not in r.anon_json
    assert "example-demo" not in json.dumps(r.anon_json, ensure_ascii=False)
