"""Unit tests for CV profile grounding, validation and sanitization against CV text."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from app.postprocess.grounding import ground_profile


class Stats:
    """Helper stats container mirroring PostprocessStats counter fields."""

    def __init__(self) -> None:
        self.contacts_nulled: int = 0
        self.names_snapped: int = 0
        self.experience_removed_ungrounded: int = 0
        self.experience_removed_type: int = 0
        self.education_removed: int = 0
        self.projects_removed: int = 0
        self.items_removed_ungrounded: int = 0
        self.bullets_merged: int = 0
        self.duplicates_removed: int = 0


def make_profile(
    *,
    full_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    github_url: str | None = None,
    objective: str | None = None,
    education: list[dict[str, Any]] | None = None,
    experience: list[dict[str, Any]] | None = None,
    personal_projects: list[dict[str, Any]] | None = None,
    skills: list[str] | None = None,
    certificates: list[str] | None = None,
    honours: list[str] | None = None,
    languages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Helper to construct a fully-formed normalized profile dict."""
    return {
        "personal_info": {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "github_url": github_url,
        },
        "objective": objective,
        "education": education if education is not None else [],
        "experience": experience if experience is not None else [],
        "personal_projects": personal_projects if personal_projects is not None else [],
        "skills": skills if skills is not None else [],
        "certificates": certificates if certificates is not None else [],
        "honours": honours if honours is not None else [],
        "languages": languages if languages is not None else [],
    }


def test_company_fake_removed_and_real_kept() -> None:
    """Ungrounded companies are removed while companies present in the CV are kept."""
    cv = (
        "Ứng viên: Nguyễn Văn A\n"
        "Kinh nghiệm:\n"
        "Công ty Cổ phần VNG - Kỹ sư phần mềm Backend (2021 - 2024)\n"
    )
    profile = make_profile(
        experience=[
            {
                "company": "Công ty Cổ phần VNG",
                "job_title": "Kỹ sư phần mềm Backend",
                "start_date": "2021",
                "end_date": "2024",
                "description": ["Phát triển microservices."],
            },
            {
                "company": "Công ty Ma Không Tồn Tại",
                "job_title": "Backend Developer",
                "start_date": "2020",
                "end_date": "2021",
                "description": ["Dự án bảo mật."],
            },
        ]
    )
    stats = Stats()
    result = ground_profile(profile, cv, stats)

    assert len(result["experience"]) == 1
    assert result["experience"][0]["company"] == "Công ty Cổ phần VNG"
    assert stats.experience_removed_ungrounded == 1


def test_company_snap_near_miss() -> None:
    """Near-miss company names are snapped to the exact source CV text."""
    cv = "Kinh nghiệm làm việc tại Công ty FPT Software từ năm 2020 đến 2023."
    profile = make_profile(
        experience=[
            {
                "company": "Cong ty FPT Softwar",
                "job_title": "Software Engineer",
                "start_date": "2020",
                "end_date": "2023",
                "description": [],
            }
        ]
    )
    stats = Stats()
    result = ground_profile(profile, cv, stats)

    assert len(result["experience"]) == 1
    assert result["experience"][0]["company"] == "Công ty FPT Software"
    assert stats.names_snapped == 1


def test_contacts_fake_nulled_and_phone_variant() -> None:
    """Fake contact fields become None; phone matches cross-format variants (84 / 0)."""
    cv = (
        "Họ và tên: Nguyễn Văn A\n"
        "Email: real_email@example.com\n"
        "Điện thoại: 0912345678\n"
        "GitHub: github.com/realuser\n"
    )
    profile = make_profile(
        full_name="Bịa Tên Ai Đó",
        email="fake_email@domain.com",
        phone="+84 912 345 678",  # Starts with 84, matches 0912345678 in CV
        github_url="https://github.com/fakeuser/",
    )
    stats = Stats()
    result = ground_profile(profile, cv, stats)

    p_info = result["personal_info"]
    assert p_info["full_name"] is None
    assert p_info["email"] is None
    assert p_info["github_url"] is None
    assert p_info["phone"] == "+84 912 345 678"  # Kept!
    assert stats.contacts_nulled == 3  # full_name, email, github_url


def test_phone_reverse_variant_and_invalid_digits() -> None:
    """Phone starting with 0 matches CV with 84; phone with < 8 digits becomes None."""
    cv = "Liên hệ: +84 912 345 678"
    profile = make_profile(phone="0912345678")
    stats = Stats()
    result = ground_profile(profile, cv, stats)
    assert result["personal_info"]["phone"] == "0912345678"

    # Invalid length (< 8 digits)
    short_profile = make_profile(phone="123456")
    stats_short = Stats()
    res_short = ground_profile(short_profile, cv, stats_short)
    assert res_short["personal_info"]["phone"] is None
    assert stats_short.contacts_nulled == 1


def test_experience_title_student_removed() -> None:
    """Job titles matching student/học viên/sinh viên are removed."""
    cv = "Công ty Cổ phần Công nghệ Alpha"
    profile = make_profile(
        experience=[
            {
                "company": "Công ty Cổ phần Công nghệ Alpha",
                "job_title": "Sinh viên",
                "start_date": None,
                "end_date": None,
                "description": [],
            },
            {
                "company": "Công ty Cổ phần Công nghệ Alpha",
                "job_title": "Student",
                "start_date": None,
                "end_date": None,
                "description": [],
            },
            {
                "company": "Công ty Cổ phần Công nghệ Alpha",
                "job_title": "Học viên",
                "start_date": None,
                "end_date": None,
                "description": [],
            },
        ]
    )
    stats = Stats()
    result = ground_profile(profile, cv, stats)
    assert len(result["experience"]) == 0
    assert stats.experience_removed_type == 3


def test_experience_school_role_rules() -> None:
    """School as company: teaching/staff roles kept; developer/student roles removed."""
    cv = "Trường Đại học Bách Khoa Hà Nội"
    profile = make_profile(
        experience=[
            {
                "company": "Trường Đại học Bách Khoa Hà Nội",
                "job_title": "Giảng viên",
                "start_date": "2018",
                "end_date": "2023",
                "description": ["Giảng dạy môn Hệ phân tán."],
            },
            {
                "company": "Trường Đại học Bách Khoa Hà Nội",
                "job_title": "Developer",
                "start_date": "2020",
                "end_date": "2022",
                "description": ["Lập trình web."],
            },
            {
                "company": "Trường Đại học Bách Khoa Hà Nội",
                "job_title": "Trợ giảng môn Python",
                "start_date": "2021",
                "end_date": "2022",
                "description": [],
            },
        ]
    )
    stats = Stats()
    result = ground_profile(profile, cv, stats)

    # Developer role is removed, Giảng viên and Trợ giảng kept
    assert len(result["experience"]) == 2
    titles = [e["job_title"] for e in result["experience"]]
    assert "Giảng viên" in titles
    assert "Trợ giảng môn Python" in titles
    assert "Developer" not in titles
    assert stats.experience_removed_type == 1


def test_experience_internship_kept() -> None:
    """Intern and thực tập sinh titles are real employment and MUST be kept."""
    cv = "Công ty TNHH Phần Mềm FPT"
    profile = make_profile(
        experience=[
            {
                "company": "Công ty TNHH Phần Mềm FPT",
                "job_title": "Thực tập sinh Backend",
                "start_date": "2023",
                "end_date": "2023",
                "description": ["Hỗ trợ viết test API."],
            },
            {
                "company": "Công ty TNHH Phần Mềm FPT",
                "job_title": "Backend Intern",
                "start_date": "2023",
                "end_date": "2023",
                "description": ["Thực tập phát triển."],
            },
        ]
    )
    stats = Stats()
    result = ground_profile(profile, cv, stats)
    assert len(result["experience"]) == 2
    assert stats.experience_removed_type == 0


def test_merge_bullets_into_project() -> None:
    """Ungrounded experience matching a project name merges description bullets without duplication."""
    cv = "Dự án Task Management App\nSử dụng FastAPI và PostgreSQL."
    profile = make_profile(
        personal_projects=[
            {
                "name": "Task Management App",
                "role": "Team Leader",
                "team_size": 3,
                "start_date": "2023",
                "end_date": "2023",
                "github_url": None,
                "description": ["Xây dựng backend với FastAPI."],
                "tech_stack": ["FastAPI", "PostgreSQL"],
            }
        ],
        experience=[
            {
                "company": "Task Management App Project",
                "job_title": "Developer",
                "start_date": "2023",
                "end_date": "2023",
                "description": [
                    "Xây dựng backend với FastAPI.",  # Duplicate bullet
                    "Tối ưu truy vấn PostgreSQL.",   # New bullet
                ],
            }
        ],
    )
    stats = Stats()
    result = ground_profile(profile, cv, stats)

    # Experience was ungrounded and removed
    assert len(result["experience"]) == 0
    assert stats.experience_removed_ungrounded == 1

    # Project received the new bullet
    proj = result["personal_projects"][0]
    assert proj["description"] == [
        "Xây dựng backend với FastAPI.",
        "Tối ưu truy vấn PostgreSQL.",
    ]
    assert stats.bullets_merged == 1


def test_education_and_projects_grounding() -> None:
    """Fake school and project names are removed; real ones snap and are kept."""
    cv = (
        "Học vấn:\n"
        "Đại học Bách Khoa Hà Nội\n"
        "Dự án cá nhân:\n"
        "Chatbot AI Tiếng Việt\n"
    )
    profile = make_profile(
        education=[
            {
                "school": "Đại học Bách Khoa Hà Nội",
                "major": "Khoa học máy tính",
                "start_year": "2019",
                "end_year": "2023",
                "gpa": "3.6",
            },
            {
                "school": "Đại học Harvard Bịa Đặt",
                "major": "IT",
                "start_year": "2019",
                "end_year": "2023",
                "gpa": None,
            },
            {
                "school": "Dai hoc Bach Khoa Ha Noi",  # Near-miss snap
                "major": "CNTT",
                "start_year": "2019",
                "end_year": "2023",
                "gpa": None,
            },
        ],
        personal_projects=[
            {
                "name": "Chatbot AI Tiếng Việt",
                "role": "Developer",
                "team_size": 1,
                "start_date": None,
                "end_date": None,
                "github_url": None,
                "description": [],
                "tech_stack": [],
            },
            {
                "name": "Dự án Không Tồn Tại",
                "role": "Lead",
                "team_size": 2,
                "start_date": None,
                "end_date": None,
                "github_url": None,
                "description": [],
                "tech_stack": [],
            },
        ],
    )
    stats = Stats()
    result = ground_profile(profile, cv, stats)

    # Education: 1 removed, 1 kept original, 1 snapped
    assert len(result["education"]) == 2
    schools = [e["school"] for e in result["education"]]
    assert "Đại học Harvard Bịa Đặt" not in schools
    assert stats.education_removed == 1

    # Personal projects: 1 kept, 1 removed
    assert len(result["personal_projects"]) == 1
    assert result["personal_projects"][0]["name"] == "Chatbot AI Tiếng Việt"
    assert stats.projects_removed == 1


def test_objective_grounding() -> None:
    """Objective with CV support is kept; fabricated objective becomes None."""
    cv = "Mục tiêu nghề nghiệp: Trở thành chuyên gia kiến trúc giải pháp Cloud."
    profile_real = make_profile(
        objective="Trở thành chuyên gia kiến trúc giải pháp Cloud."
    )
    stats_real = Stats()
    res_real = ground_profile(profile_real, cv, stats_real)
    assert res_real["objective"] is not None
    assert stats_real.items_removed_ungrounded == 0

    profile_fake = make_profile(
        objective="Mục tiêu bịa đặt không có gì liên quan trong CV."
    )
    stats_fake = Stats()
    res_fake = ground_profile(profile_fake, cv, stats_fake)
    assert res_fake["objective"] is None
    assert stats_fake.items_removed_ungrounded == 1


def test_certificates_and_honours_grounding() -> None:
    """Real certs/honours are kept (model text preserved, no snap); fake ones removed."""
    cv = (
        "Chứng chỉ:\n"
        "AWS Certified Solutions Architect Associate\n"
        "Giải thưởng:\n"
        "Giải Nhất Cuộc thi Lập trình Sinh viên 2022\n"
    )
    profile = make_profile(
        certificates=[
            "AWS Certified Solutions Architect Associate",
            "Google Professional Cloud Architect Giả Mạo",
        ],
        honours=[
            "Giải Nhất Cuộc thi Lập trình Sinh viên 2022",
            "Huy chương Vàng Olympic Tin học Bịa",
        ],
    )
    stats = Stats()
    result = ground_profile(profile, cv, stats)

    assert result["certificates"] == ["AWS Certified Solutions Architect Associate"]
    assert result["honours"] == ["Giải Nhất Cuộc thi Lập trình Sinh viên 2022"]
    assert stats.items_removed_ungrounded == 2


def test_languages_grounding() -> None:
    """Languages checked via aliases; 1-word aliases require language context in CV."""
    # Scenario A: Candidate name has "Anh" but CV has NO language section
    cv_no_lang = (
        "Họ và tên: Nguyễn Tuấn Anh\n"
        "Vị trí: Lập trình viên Python\n"
    )
    profile_lang = make_profile(
        languages=[
            {"language": "English", "note": "TOEFL 90"},
        ]
    )
    stats_a = Stats()
    res_a = ground_profile(profile_lang, cv_no_lang, stats_a)
    assert len(res_a["languages"]) == 0
    assert stats_a.items_removed_ungrounded == 1

    # Scenario B: CV mentions "Tiếng Anh: TOEIC 750" -> English item kept
    cv_with_lang = (
        "Họ và tên: Nguyễn Tuấn Anh\n"
        "Ngoại ngữ: Tiếng Anh: TOEIC 750\n"
    )
    stats_b = Stats()
    res_b = ground_profile(profile_lang, cv_with_lang, stats_b)
    assert len(res_b["languages"]) == 1
    assert res_b["languages"][0]["language"] == "English"
    assert stats_b.items_removed_ungrounded == 0

    # Scenario C: Single word alias "Nhật" with "Ngoại ngữ" context
    cv_japanese = (
        "Họ và tên: Trần Văn B\n"
        "Ngoại ngữ: Nhật N2\n"
    )
    profile_jp = make_profile(
        languages=[
            {"language": "Japanese", "note": "JLPT N2"},
        ]
    )
    stats_c = Stats()
    res_c = ground_profile(profile_jp, cv_japanese, stats_c)
    assert len(res_c["languages"]) == 1
    assert res_c["languages"][0]["language"] == "Japanese"


def test_duplicates_removed() -> None:
    """Exact duplicate items across section lists are removed."""
    cv = "Chứng chỉ AWS SAA. Tiếng Anh TOEIC."
    profile = make_profile(
        certificates=["AWS SAA", "AWS SAA"],
        languages=[
            {"language": "Tiếng Anh", "note": "TOEIC"},
            {"language": "Tiếng Anh", "note": "TOEIC"},
        ],
    )
    stats = Stats()
    result = ground_profile(profile, cv, stats)

    assert result["certificates"] == ["AWS SAA"]
    assert len(result["languages"]) == 1
    assert stats.duplicates_removed == 2


def test_input_not_mutated() -> None:
    """Input profile dict is not mutated by ground_profile."""
    cv = "Công ty FPT Software"
    original = make_profile(
        email="fake@gmail.com",
        experience=[
            {
                "company": "Công ty Ma",
                "job_title": "Developer",
                "start_date": None,
                "end_date": None,
                "description": [],
            }
        ],
    )
    clone = copy.deepcopy(original)
    _ = ground_profile(original, cv)

    assert original == clone


def test_empty_cv_text_returns_original() -> None:
    """Empty or blank cv_text returns an unmutated clone without dropping anything."""
    profile = make_profile(
        email="fake@gmail.com",
        experience=[
            {
                "company": "Công ty Bất Kỳ",
                "job_title": "Developer",
                "start_date": None,
                "end_date": None,
                "description": [],
            }
        ],
    )
    clone = copy.deepcopy(profile)

    res_empty = ground_profile(profile, "")
    assert res_empty == clone

    res_whitespace = ground_profile(profile, "   \n\t  ")
    assert res_whitespace == clone
