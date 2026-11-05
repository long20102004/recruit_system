"""Unit tests for schema normalisation and skill cleaning.

Synthetic CV profile data only (no real PII).
"""

import copy

from app.postprocess.schema import normalize_profile
from app.postprocess.skills import clean_skill_list


class Stats:
    """Minimal stats object mirroring ``PostprocessStats`` counters."""

    def __init__(self):
        self.keys_renamed = 0
        self.types_coerced = 0
        self.skills_cleaned = 0


def _synthetic_profile() -> dict:
    return {
        "personal_info": {
            "full_name": "Nguyen Van Synthetic",
            "email": "synthetic.candidate@example.test",
        },
        "objective": "Backend intern",
        "education": [
            {
                "school": "Học viện Synthetic",
                "major": "Công nghệ thông tin",
                "start_year": 2021,
                "end_year": 2025,
            }
        ],
        "experience": [
            {
                "company": "Cong ty Synthetic",
                "job_title": "Backend Developer",
                "start_date": "2023-01",
                "end_date": "2024-01",
                "description": ["Built APIs"],
            }
        ],
        "personal_projects": [],
        "skills": ["Python", "SQL"],
        "certificates": [],
        "honours": [],
        "languages": [{"language": "English", "note": "TOEIC 700"}],
    }


def test_alias_keys_are_renamed_and_merged():
    data = {
        "honors": ["Giải nhì Olympic"],
        "honours": ["Học bổng Synthetic"],
        "certifications": ["AWS Practitioner"],
        "projects": [{"name": "Synthetic Shop"}],
    }

    result = normalize_profile(data)

    assert result["honours"] == ["Học bổng Synthetic", "Giải nhì Olympic"]
    assert result["certificates"] == ["AWS Practitioner"]
    assert result["personal_projects"][0]["name"] == "Synthetic Shop"


def test_result_contains_every_schema_key():
    result = normalize_profile(_synthetic_profile())

    assert set(result) == {
        "personal_info",
        "objective",
        "education",
        "experience",
        "personal_projects",
        "skills",
        "certificates",
        "honours",
        "languages",
    }
    assert set(result["personal_info"]) == {
        "full_name",
        "email",
        "phone",
        "github_url",
    }
    assert result["personal_info"]["phone"] is None
    assert result["personal_projects"] == []


def test_unknown_keys_are_dropped():
    data = _synthetic_profile()
    data["hobbies"] = ["chess"]
    data["personal_info"]["address"] = "Somewhere"

    result = normalize_profile(data)

    assert "hobbies" not in result
    assert "address" not in result["personal_info"]


def test_description_string_becomes_list():
    data = _synthetic_profile()
    data["experience"][0]["description"] = "Built API\n• Wrote tests"

    result = normalize_profile(data)

    assert result["experience"][0]["description"] == ["Built API", "Wrote tests"]


def test_team_size_numeric_string_and_words():
    data = {
        "personal_projects": [
            {"name": "Project A", "team_size": "4"},
            {"name": "Project B", "team_size": "bốn"},
        ]
    }

    result = normalize_profile(data)

    assert result["personal_projects"][0]["team_size"] == 4
    assert result["personal_projects"][1]["team_size"] is None


def test_experience_dict_becomes_single_item_list():
    data = {"experience": {"company": "Synthetic", "job_title": "Dev"}}

    result = normalize_profile(data)

    assert isinstance(result["experience"], list)
    assert len(result["experience"]) == 1
    assert result["experience"][0]["company"] == "Synthetic"


def test_non_dict_input_returns_empty_schema():
    result = normalize_profile(["not", "a", "dict"])

    assert result["personal_info"] == {
        "full_name": None,
        "email": None,
        "phone": None,
        "github_url": None,
    }
    assert result["skills"] == []
    assert result["experience"] == []


def test_input_is_not_mutated():
    data = _synthetic_profile()
    original = copy.deepcopy(data)

    normalize_profile(data)

    assert data == original


def test_stats_counters_are_incremented():
    stats = Stats()
    data = {"honors": ["A"], "experience": {"company": "X", "job_title": "Dev"}}

    normalize_profile(data, stats)

    assert stats.keys_renamed == 1
    assert stats.types_coerced >= 1


def test_skill_group_label_is_stripped():
    assert clean_skill_list(["Backend: Spring Boot"]) == ["Spring Boot"]


def test_skill_with_parentheses_is_kept_intact():
    assert clean_skill_list(["Spring Boot (Web, Data JPA)"]) == [
        "Spring Boot (Web, Data JPA)"
    ]


def test_skills_dedupe_case_insensitively_keeping_first():
    assert clean_skill_list(["java", "Java", "JAVA"]) == ["java"]


def test_empty_skill_items_are_dropped():
    assert clean_skill_list(["", "  ", "Python"]) == ["Python"]


def test_skill_stats_count_changed_items():
    stats = Stats()

    clean_skill_list(["Backend: Spring Boot", "java", "Java", ""], stats)

    assert stats.skills_cleaned == 3


def test_alias_and_canonical_list_values_are_concatenated():
    result = normalize_profile({"honors": ["X"], "honours": "Y"})

    assert result["honours"] == ["Y", "X"]

    result = normalize_profile({"skill": "Python", "skills": ["SQL"]})

    assert result["skills"] == ["SQL", "Python"]


def test_clean_skill_list_splits_grouped_delimiters():
    assert clean_skill_list(["Ngôn ngữ lập trình: Python, C++"]) == [
        "Python",
        "C++",
    ]
    assert clean_skill_list(["Python; SQL | Docker\nGo"]) == [
        "Python",
        "SQL",
        "Docker",
        "Go",
    ]


def test_clean_skill_list_keeps_parentheses_and_slashes():
    assert clean_skill_list(["Spring Boot (Web, Data JPA)", "HTML/CSS"]) == [
        "Spring Boot (Web, Data JPA)",
        "HTML/CSS",
    ]


def test_schema_string_sections_are_split_top_level():
    result = normalize_profile(
        {
            "skills": "Python, C++",
            "certificates": "AWS, Practitioner\nAzure; GCP",
            "honours": "Giải nhì, Olympic\nHọc bổng; Thành tích",
            "personal_projects": [{"name": "P", "tech_stack": "Python, SQL"}],
        }
    )

    assert result["skills"] == ["Python", "C++"]
    assert result["certificates"] == ["AWS, Practitioner", "Azure", "GCP"]
    assert result["honours"] == ["Giải nhì, Olympic", "Học bổng", "Thành tích"]
    assert result["personal_projects"][0]["tech_stack"] == ["Python", "SQL"]


def test_team_size_extracts_first_integer():
    result = normalize_profile(
        {
            "personal_projects": [
                {"name": "A", "team_size": "4 người"},
                {"name": "B", "team_size": "nhóm 12 thành viên"},
                {"name": "C", "team_size": "bốn"},
            ]
        }
    )

    assert result["personal_projects"][0]["team_size"] == 4
    assert result["personal_projects"][1]["team_size"] == 12
    assert result["personal_projects"][2]["team_size"] is None



def test_unbalanced_brackets_from_a_cut_group_are_repaired():
    """Model cut "AWS (IAM, S3, EC2, CloudWatch)" at its commas (feature 011)."""
    from app.postprocess.skills import clean_skill_list

    out = clean_skill_list(["AWS (IAM", "S3", "EC2", "CloudWatch)", "Kubernetes Provider)", "Spring Boot (Web, Data JPA)"])
    assert out == ["AWS", "IAM", "S3", "EC2", "CloudWatch", "Kubernetes Provider", "Spring Boot (Web, Data JPA)"]
