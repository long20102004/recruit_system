"""Tests for cleanup_profile (feature 012: output completion cleanup).

Covers:
- FR-2a: Drop experience whose company equals a personal project name.
- FR-2b: Drop experience whose company is only an address (and keep real companies).
- FR-3: Drop junk skills (bare digits, punctuation, > 8 words) and keep valid skills.
- Pipeline integration and PostprocessStats counters.
"""

from __future__ import annotations

import copy
from typing import Any

from app.postprocess.cleanup import (
    cleanup_profile,
    is_address_only_company,
    is_junk_skill,
)
from app.postprocess.pipeline import PostprocessStats, postprocess


def test_is_junk_skill():
    # Junk cases: bare digits, punctuation, spaces, > 8 words
    assert is_junk_skill("815") is True
    assert is_junk_skill("100") is True
    assert is_junk_skill("...") is True
    assert is_junk_skill("-") is True
    assert is_junk_skill("---") is True
    assert is_junk_skill("   ") is True
    assert is_junk_skill(None) is True
    assert is_junk_skill(815) is True
    assert is_junk_skill("one two three four five six seven eight nine") is True
    assert is_junk_skill("Thành thạo lập trình hướng đối tượng với ngôn ngữ Java và Spring") is True

    # Valid cases: must NOT be dropped
    assert is_junk_skill("C++") is False
    assert is_junk_skill("Node.js") is False
    assert is_junk_skill("3D Modeling") is False
    assert is_junk_skill("C#") is False
    assert is_junk_skill(".NET Core") is False
    assert is_junk_skill("CI/CD") is False
    assert is_junk_skill("HTML5") is False
    # Exactly 8 words must be kept
    assert is_junk_skill("one two three four five six seven eight") is False


def test_is_address_only_company():
    # Address-only cases: 63 provinces, country, and admin phrases
    assert is_address_only_company("Hà Nội") is True
    assert is_address_only_company("TP. Hồ Chí Minh") is True
    assert is_address_only_company("Đà Nẵng") is True
    assert is_address_only_company("Vĩnh Phúc") is True
    assert is_address_only_company("Tỉnh Bình Dương") is True
    assert is_address_only_company("Ha Noi, Viet Nam") is True
    assert is_address_only_company("Da Nang, Vietnam") is True
    assert is_address_only_company("Hai Phong") is True
    assert is_address_only_company("Can Tho City") is True

    # Locality with >= 2 administrative terms
    assert is_address_only_company("Phường Dịch Vọng Hậu, Quận Cầu Giấy, Hà Nội") is True
    assert is_address_only_company("Quận 1, Thành phố Hồ Chí Minh") is True
    assert is_address_only_company("123 Đường Láng, Phường Láng Thượng, Quận Đống Đa") is True
    assert is_address_only_company("Ward 2, District 3, Ho Chi Minh City") is True
    assert is_address_only_company("Xã Phước Kiển, Huyện Nhà Bè, Tỉnh Đồng Nai") is True

    # Real company names: must NOT be flagged as address-only
    assert is_address_only_company("FPT Software Hà Nội") is False
    assert is_address_only_company("Công ty Cổ phần Công nghệ ABC Đà Nẵng") is False
    assert is_address_only_company("Viettel Telecom Hồ Chí Minh") is False
    assert is_address_only_company("Shopee Vietnam") is False
    assert is_address_only_company("VNG Corporation") is False
    assert is_address_only_company("Bệnh viện Đa khoa Tỉnh Bình Dương") is False
    assert is_address_only_company("") is False
    assert is_address_only_company(None) is False


def test_fr2a_drop_experience_matching_project():
    profile = {
        "experience": [
            {"company": "E-Commerce Website", "job_title": "Frontend Developer"},
            {"company": "Web bán hàng", "job_title": "Fullstack Developer"},
            {"company": "FPT Software", "job_title": "Software Engineer"},
        ],
        "personal_projects": [
            {"name": "E-Commerce Website", "description": ["React application"]},
            {"name": "WEB BÁN HÀNG", "description": ["Django site"]},
        ],
    }
    stats = PostprocessStats()
    res = cleanup_profile(profile, stats)

    assert len(res["experience"]) == 1
    assert res["experience"][0]["company"] == "FPT Software"
    assert stats.experience_removed_project == 2
    # Personal projects are preserved
    assert len(res["personal_projects"]) == 2


def test_fr2a_keep_experience_not_matching_project():
    profile = {
        "experience": [
            {"company": "Google LLC", "job_title": "Engineer"},
            {"company": "FPT Software", "job_title": "Developer"},
        ],
        "personal_projects": [
            {"name": "Personal Blog", "description": ["Next.js"]},
        ],
    }
    stats = PostprocessStats()
    res = cleanup_profile(profile, stats)

    assert len(res["experience"]) == 2
    assert stats.experience_removed_project == 0


def test_fr2b_drop_address_only_experience():
    profile = {
        "experience": [
            {"company": "Hà Nội", "job_title": "Developer"},
            {"company": "TP. Hồ Chí Minh", "job_title": "Lead"},
            {"company": "Phường Dịch Vọng Hậu, Quận Cầu Giấy, Hà Nội", "job_title": "Dev"},
            {"company": "FPT Software Hà Nội", "job_title": "Senior Dev"},
        ],
        "personal_projects": [],
    }
    stats = PostprocessStats()
    res = cleanup_profile(profile, stats)

    assert len(res["experience"]) == 1
    assert res["experience"][0]["company"] == "FPT Software Hà Nội"
    assert stats.experience_removed_address == 3


def test_fr2b_keep_real_companies():
    companies = [
        "FPT Software Hà Nội",
        "Công ty Cổ phần Công nghệ ABC Đà Nẵng",
        "Viettel Telecom Hồ Chí Minh",
        "Shopee Vietnam",
        "Bệnh viện Đa khoa Tỉnh Bình Dương",
    ]
    profile = {
        "experience": [{"company": c, "job_title": "Developer"} for c in companies],
        "personal_projects": [],
    }
    stats = PostprocessStats()
    res = cleanup_profile(profile, stats)

    assert len(res["experience"]) == len(companies)
    assert stats.experience_removed_address == 0


def test_fr3_skills_and_project_tech_stack_cleaning():
    profile = {
        "skills": [
            "815",
            "...",
            "-",
            "C++",
            "Node.js",
            "3D Modeling",
            "one two three four five six seven eight",  # exactly 8 words -> keep
            "one two three four five six seven eight nine",  # 9 words -> drop
            "Thành thạo lập trình hướng đối tượng với ngôn ngữ Java và Spring Boot",  # >8 words -> drop
        ],
        "personal_projects": [
            {
                "name": "Game 3D",
                "tech_stack": [
                    "815",
                    "3D Modeling",
                    "C++",
                    "-",
                ],
            }
        ],
    }
    stats = PostprocessStats()
    res = cleanup_profile(profile, stats)

    # 5 junk skills dropped from profile["skills"]: "815", "...", "-", 9-word sentence, long Vietnamese sentence
    assert res["skills"] == [
        "C++",
        "Node.js",
        "3D Modeling",
        "one two three four five six seven eight",
    ]

    # 2 junk items dropped from project["tech_stack"]: "815", "-"
    assert res["personal_projects"][0]["tech_stack"] == [
        "3D Modeling",
        "C++",
    ]

    # Total junk skills removed across skills + tech_stack = 5 + 2 = 7
    assert stats.skills_removed_junk == 7


def test_cleanup_profile_without_stats():
    profile = {
        "experience": [
            {"company": "Hà Nội", "job_title": "Developer"},
            {"company": "Project Alpha", "job_title": "Developer"},
            {"company": "Acme Corp", "job_title": "Developer"},
        ],
        "personal_projects": [
            {"name": "Project Alpha", "tech_stack": ["815", "Python"]},
        ],
        "skills": ["...", "Java"],
    }
    res = cleanup_profile(profile, stats=None)
    assert len(res["experience"]) == 1
    assert res["experience"][0]["company"] == "Acme Corp"
    assert res["personal_projects"][0]["tech_stack"] == ["Python"]
    assert res["skills"] == ["Java"]


def test_pipeline_integration_with_cleanup():
    synthetic_cv = """
    HỌ VÀ TÊN: Trần Văn B
    Email: tran.van.b@example.com
    Số điện thoại: 0912345678

    KINH NGHIỆM LÀM VIỆC
    FPT Software Hà Nội
    Vị trí: Backend Engineer (2021 - 2023)
    - Xây dựng hệ thống microservices.

    DỰ ÁN
    Web bán hàng
    Mô tả: Hệ thống thương mại điện tử.

    KỸ NĂNG
    Java, C++, Node.js, 3D Modeling
    """

    synthetic_raw_output = {
        "personal_info": {
            "full_name": "Trần Văn B",
            "email": "tran.van.b@example.com",
            "phone": "0912345678",
        },
        "experience": [
            {
                "company": "FPT Software Hà Nội",
                "job_title": "Backend Engineer",
                "start_date": "2021",
                "end_date": "2023",
            },
            {
                "company": "Web bán hàng",
                "job_title": "Developer",
                "start_date": "2020",
                "end_date": "2021",
            },
            {
                "company": "Hà Nội",
                "job_title": "Freelancer",
                "start_date": "2019",
                "end_date": "2020",
            },
        ],
        "personal_projects": [
            {
                "name": "Web bán hàng",
                "tech_stack": ["Java", "815"],
            }
        ],
        "skills": ["Java", "C++", "Node.js", "3D Modeling", "...", "815"],
    }

    profile, stats = postprocess(synthetic_raw_output, synthetic_cv)

    # Experience:
    # "Web bán hàng" dropped by FR-2a (matches project name)
    # "Hà Nội" dropped by FR-2b (address only)
    # "FPT Software Hà Nội" kept
    companies = [e["company"] for e in profile.get("experience", [])]
    assert "FPT Software Hà Nội" in companies
    assert "Web bán hàng" not in companies
    assert "Hà Nội" not in companies

    # Skills:
    # "..." and "815" dropped by FR-3
    # "Java", "C++", "Node.js", "3D Modeling" kept
    assert "C++" in profile["skills"]
    assert "Node.js" in profile["skills"]
    assert "3D Modeling" in profile["skills"]
    assert "..." not in profile["skills"]
    assert "815" not in profile["skills"]

    # Tech stack in project:
    # "815" dropped
    assert "815" not in profile["personal_projects"][0]["tech_stack"]
    assert "Java" in profile["personal_projects"][0]["tech_stack"]

    # Stats counters verify
    stats_dict = stats.as_dict()
    assert stats_dict.get("experience_removed_project", 0) >= 1
    assert stats_dict.get("experience_removed_address", 0) >= 1
    assert stats_dict.get("skills_removed_junk", 0) >= 1
