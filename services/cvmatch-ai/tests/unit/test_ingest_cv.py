"""T04: Luong A, A1-A9. Test vang = CV mau cua thiet ke 04 (cac bang 'Ket qua va noi luu')."""

import copy
import json

import pytest

from cvmatch.core.config import load_config
from cvmatch.core.text.normalize import strip_diacritics
from cvmatch.ingest.cv.a03_anonymize import scrub_text, _name_regex
from cvmatch.ingest.cv.a07_bullets import split_description
from cvmatch.ingest.cv.pipeline import build_cv_record
from cvmatch.ingest.cv.record import CvContext, DuplicateCV, InMemoryDedup
from cvmatch.ingest.cv.schema import InvalidCV

from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

SAMPLE = json.loads((FIXTURES / "cv" / "cv_sample.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ctx(kb_mini):
    return CvContext.create(load_config(), kb_mini, hmac_key="test-key", ingest_ym="2026-11")


@pytest.fixture(scope="module")
def rec(ctx):
    return build_cv_record(copy.deepcopy(SAMPLE), ctx)


def cv_with(**changes):
    d = copy.deepcopy(SAMPLE)
    d.update(changes)
    return d


# ------------------------------------------------------------------ test vang CV mau


def test_a05_cv_skill_table(rec):
    got = {s.skill_id: (s.ev, s.source_field, s.evidence_snippet, s.last_used) for s in rec.skills_found}
    assert got == {
        "S0002": (1.0, "experiences[0].description[0]", "xây dựng api thanh toán bằng spring boot", "2026-11"),
        "S0015": (1.0, "experiences[0].description[1]", "tối ưu truy vấn postgresql, giảm 40% thời gian", "2026-11"),
        "S0001": (0.8, "experiences[0].technologies[0]", "java", "2026-11"),       # Java
        "S0021": (0.8, "experiences[0].technologies[2]", "kafka", "2026-11"),      # Kafka
        "S0019": (0.6, "skills[3]", "docker", None),                               # Docker
    }
    refs = {s.skill_id: s.bullet_ref for s in rec.skills_found}
    assert refs["S0002"] == ("experience", 0, 0) and refs["S0015"] == ("experience", 0, 1)
    assert refs["S0019"] is None
    assert rec.unknown_skills == []


def test_a06_meta(rec):
    m = rec.meta
    assert m.location == "ho_chi_minh"
    assert m.years_experience == 4.7          # 2022-03 .. 2026-11 (dang lam) = 56 thang
    assert m.intern_months == 0
    assert (m.role_group, m.level_rank, m.level_source) == ("Backend", 4, "title")
    assert m.major_group == "it"
    (e,) = rec.experiences
    assert (e.kind, e.title_raw, e.role_group, e.role_group_src, e.start_ym, e.end_ym, e.months,
            e.dates_quality) == ("job", "senior java developer", "Backend", "rule", "2022-03", "2026-11",
                                 56, "ok")
    (ed,) = rec.education
    assert (ed.major_raw, ed.major_group, ed.status, ed.end_year) == ("kỹ thuật phần mềm", "it", "graduated", 2020)


def test_a07_bullets(rec):
    assert rec.meta.n_bullets == 2
    b0, b1 = rec.bullets
    assert (b0.section, b0.item_idx, b0.pos) == ("experience", 0, 0)
    assert b0.text_raw == "Xây dựng API thanh toán bằng Spring Boot"
    assert b0.context_text == "senior java developer: xây dựng api thanh toán bằng spring boot"
    assert b1.text_raw == "Tối ưu truy vấn PostgreSQL, giảm 40% thời gian"
    assert b1.context_text == "senior java developer: tối ưu truy vấn postgresql, giảm 40% thời gian"
    assert not (b0.has_negation or b0.is_coursework or b1.has_negation or b1.is_coursework)


def test_a08_doc_text(rec):
    assert rec.doc_text == (
        "Chức danh: senior java developer\n"
        "Tóm tắt: backend developer 4 năm kinh nghiệm java\n"
        "Kinh nghiệm: senior java developer. xây dựng api thanh toán bằng spring boot. "
        "tối ưu truy vấn postgresql, giảm 40% thời gian. Công nghệ: java, spring boot, kafka\n"
        "Dự án: (không có)\n"
        "Kỹ năng: java, spring boot, postgresql, docker\n"
        "Học vấn: kỹ thuật phần mềm"
    )


def test_a09_bm25(rec):
    b = rec.bm25
    assert b.skill_tokens == ["skill_s0001", "skill_s0002", "skill_s0015", "skill_s0019", "skill_s0021"]
    assert "xây_dựng" in b.bm25_acc and "xay_dung" in b.bm25_noacc
    assert "thanh_toán" in b.bm25_acc and "thanh_toan" in b.bm25_noacc
    assert len(b.bm25_acc) == len(b.bm25_noacc)
    assert "chức_danh" not in b.bm25_acc and "chức" not in b.bm25_acc   # nhan dong khong vao BM25


def test_a01_a02_record_header(rec):
    assert rec.raw_json["experiences"][0]["is_current"] is True
    assert rec.raw_json["education"][0]["end"] == "2020-12"   # A1 sua ngay
    assert rec.flags == []
    assert len(rec.content_hash) == 64
    assert rec.candidate_key.startswith("hmac:") and "a.nguyen" not in rec.candidate_key
    assert (rec.version, rec.is_latest) == (1, True)
    assert rec.ontology_version == "kb-mini-test" and rec.pipeline_version == "prep-1.1"


# ------------------------------------------------------------------ an danh


def test_a03_anonymized_no_pii(rec):
    dumped = json.dumps(rec.anon_json, ensure_ascii=False).lower() + rec.doc_text.lower()
    for pii in ("nguyễn văn a", "a.nguyen@example.com", "0901234567", "1998", "bách khoa"):
        assert pii not in dumped
    assert "school" not in rec.anon_json["education"][0]
    assert rec.raw_json["full_name"] == "Nguyễn Văn A"  # vung goc van giu


def test_a03_scrub_name_email_phone_in_free_text(ctx):
    d = cv_with(summary="Tôi là Nguyễn Văn A (nguyen van a), email a@x.vn, sđt +84 901 234 567. "
                        "Backend developer.")
    r = build_cv_record(d, ctx)
    s = r.anon_json["summary"]
    assert "nguyễn văn a" not in s and "nguyen van a" not in s
    assert "a@x.vn" not in s and "901" not in s
    assert "backend developer" in s


def test_scrub_keeps_normal_numbers():
    assert scrub_text("Giảm 40% thời gian trong 2023", _name_regex("Trần B")) == "Giảm 40% thời gian trong 2023"


# ------------------------------------------------------------------ A1, A2


def test_a01_invalid_schema(ctx):
    with pytest.raises(InvalidCV) as e:
        build_cv_record(cv_with(experiences="không phải danh sách"), ctx)
    assert e.value.errors[0]["loc"][0] == "experiences"
    with pytest.raises(InvalidCV):
        build_cv_record(["không phải object"], ctx)


def test_a01_flags_date_unparsed_and_low_content(ctx):
    d = cv_with()
    d["experiences"][0]["start"] = "mùa xuân năm ngoái"
    r = build_cv_record(d, ctx)
    assert "date_unparsed" in r.flags and "years_uncertain" in r.flags
    assert r.meta.years_experience is None
    assert r.experiences[0].dates_quality == "missing"

    r2 = build_cv_record({"full_name": "X", "email": "x@y.z", "summary": "Tôi thích lập trình"}, ctx)
    assert "low_content" in r2.flags and r2.meta.years_experience == 0.0


def test_a02_duplicate_and_new_version(kb_mini):
    dedup = InMemoryDedup()
    c = CvContext.create(load_config(), kb_mini, hmac_key="k", ingest_ym="2026-11", dedup=dedup)
    r1 = build_cv_record(copy.deepcopy(SAMPLE), c)
    dedup.add(r1)
    with pytest.raises(DuplicateCV) as e:
        build_cv_record(copy.deepcopy(SAMPLE), c)
    assert e.value.existing_cv_id == r1.cv_id
    r2 = build_cv_record(cv_with(summary="Backend developer 5 năm", email=" A.Nguyen@Example.com "), c)
    assert (r2.version, r2.replaces_cv_id, r2.candidate_key) == (2, r1.cv_id, r1.candidate_key)


def test_a02_no_identity(ctx):
    d = cv_with()
    d.pop("email"), d.pop("phone")
    assert "no_identity" in build_cv_record(d, ctx).flags
    d2 = cv_with(email=None, phone="+84 901 234 567")
    d3 = cv_with(email=None, phone="0901234567")
    assert build_cv_record(d2, ctx).candidate_key == build_cv_record(d3, ctx).candidate_key


# ------------------------------------------------------------------ A6 so nam, A4 khong dau, A7 co


def test_a06_overlap_merged(ctx):
    d = cv_with(experiences=[
        {"title": "Java Developer", "start": "2019-01", "end": "2020-06", "description": []},
        {"title": "Backend Developer", "start": "2020-03", "end": "2022-12", "description": []},
    ])
    r = build_cv_record(d, ctx)
    assert r.meta.years_experience == 4.0          # 48 thang, khong phai 52
    assert [e.title_raw for e in r.experiences] == ["backend developer", "java developer"]  # moi -> cu


def test_a06_intern_separate_and_inferred_level(ctx):
    d = cv_with(experiences=[
        {"title": "Thực tập sinh Tester", "start": "2021-01", "end": "2021-06"},
        {"title": "Lập trình viên Java", "start": "2021-07", "end": "2023-06"},
    ])
    r = build_cv_record(d, ctx)
    assert r.meta.intern_months == 6
    assert r.meta.years_experience == 2.0
    assert (r.meta.level_rank, r.meta.level_source) == (2, "inferred")   # 2 nam -> Junior
    assert r.experiences[1].kind == "intern"


def test_a06_role_by_keywords(ctx):
    d = cv_with(experiences=[{
        "title": "Kỹ sư phần mềm", "start": "2023-01", "end": "2024-01",
        "description": ["Viết test case và kiểm thử tự động bằng Selenium", "Báo cáo bug cho đội phát triển"],
    }])
    e = build_cv_record(d, ctx).experiences[0]
    assert (e.role_group, e.role_group_src) == ("QA", "keyword")


def test_a06_education_studying(ctx):
    d = cv_with(education=[{"school": "ĐH X", "major": "Công nghệ thông tin", "end": "đang học"}])
    (ed,) = build_cv_record(d, ctx).education
    assert ed.status == "studying"
    d2 = cv_with(education=[{"school": "ĐH X", "major": "Toán tin", "end": "06/2027"}])
    (ed2,) = build_cv_record(d2, ctx).education
    assert (ed2.status, ed2.expected_end_ym, ed2.major_group) == ("studying", "2027-06", "related")


def test_a04_no_diacritics_flag(ctx):
    d = cv_with(summary=strip_diacritics("Lập trình viên backend có kinh nghiệm xây dựng hệ thống "
                                         "thanh toán cho khách hàng doanh nghiệp và tối ưu cơ sở dữ liệu"))
    d["experiences"][0]["description"] = [strip_diacritics(x) for x in d["experiences"][0]["description"]]
    assert "no_diacritics" in build_cv_record(d, ctx).flags


def test_a07_flags_and_paragraph_split(ctx):
    d = cv_with(projects=[{
        "name": "Đồ án tốt nghiệp",
        "description": "• Bài tập lớn môn Cơ sở dữ liệu: thiết kế CSDL thư viện\n"
                       "• Chưa từng triển khai Kubernetes trên production. Tự học Docker qua tài liệu.\n"
                       "03/2020 - 06/2021\n- Ngắn quá",
    }])
    r = build_cv_record(d, ctx)
    pb = [b for b in r.bullets if b.section == "project"]
    assert [b.text_raw for b in pb] == [
        "Bài tập lớn môn Cơ sở dữ liệu: thiết kế CSDL thư viện",
        "Chưa từng triển khai Kubernetes trên production.",
        "Tự học Docker qua tài liệu.",
    ]
    assert pb[0].is_coursework and pb[1].has_negation
    assert pb[0].context_text.startswith("đồ án tốt nghiệp: ")
    assert r.meta.n_bullets == 2 + 3


def test_split_description_keeps_tech_dots():
    parts = split_description("Dùng Node.js và ASP.NET Core cho API. Viết 3.5 nghìn dòng test.", 4)
    assert [p.raw for p in parts] == ["Dùng Node.js và ASP.NET Core cho API.", "Viết 3.5 nghìn dòng test."]


def test_unknown_skill(ctx):
    d = cv_with(skills=["Java", "Figma", "Làm việc nhóm tốt và chịu được áp lực công việc cao"])
    r = build_cv_record(d, ctx)
    assert [u.text for u in r.unknown_skills] == ["figma"]   # cum dai qua khong coi la ten ky nang


def test_deterministic(ctx):
    a = build_cv_record(copy.deepcopy(SAMPLE), ctx).model_dump(exclude={"cv_id"})
    b = build_cv_record(copy.deepcopy(SAMPLE), ctx).model_dump(exclude={"cv_id"})
    assert a == b
