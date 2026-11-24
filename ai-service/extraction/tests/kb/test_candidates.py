"""Unit tests for CandidateSkillFinder."""

from __future__ import annotations

import csv
from pathlib import Path
import time

import pytest

from app.kb.candidates import CandidateSkillFinder


@pytest.fixture
def seed_dir(tmp_path: Path) -> Path:
    """Create a synthetic seed directory with skills.csv and skill_aliases.csv."""
    skills_csv = tmp_path / "skills.csv"
    with skills_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "category", "reviewed"])
        writer.writerow([1, "Java", "Backend", "true"])
        writer.writerow([2, "JavaScript", "Frontend", "true"])
        writer.writerow([3, "Go", "Backend", "true"])
        writer.writerow([4, "Python", "Backend", "true"])
        writer.writerow([5, "PostgreSQL", "Database", "true"])
        writer.writerow([6, "C", "Programming Language", "true"])
        writer.writerow([7, "C#", "Programming Language", "true"])
        writer.writerow([8, "C++", "Programming Language", "true"])
        writer.writerow([9, "React", "Frontend", "true"])
        writer.writerow([10, "Communication", "Soft Skill", "true"])
        writer.writerow(
            [
                11,
                "Skill Name That Is Way Too Long And Exceeds Forty Characters In Total Length",
                "Soft Skill",
                "true",
            ]
        )

    aliases_csv = tmp_path / "skill_aliases.csv"
    with aliases_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["alias_key", "skill_id", "surface"])
        writer.writerow(["postgres", 5, "Postgres"])
        writer.writerow(["js", 2, "JS"])
        writer.writerow(["golang", 3, "Golang"])
        writer.writerow(["reactjs", 9, "ReactJS"])
        writer.writerow(["react", 9, "React"])
        writer.writerow(
            [
                "toolongalias",
                1,
                "This alias surface also exceeds forty characters in total length",
            ]
        )

    return tmp_path


def test_alias_maps_to_canonical(seed_dir: Path) -> None:
    finder = CandidateSkillFinder.from_csv(seed_dir)
    res = finder.find("Tôi sử dụng Postgres để lưu trữ dữ liệu.")
    assert res == ["PostgreSQL"]


def test_go_boundary_and_case(seed_dir: Path) -> None:
    finder = CandidateSkillFinder.from_csv(seed_dir)

    # "Google" or "go to" must NOT match "Go"
    assert finder.find("I work at Google and go to school.") == []

    # Standalone "Go" must match
    assert finder.find("Kinh nghiệm lập trình Go và Python.") == ["Go", "Python"]

    # Alias "Golang" matches canonical "Go"
    assert finder.find("Thành thạo Golang.") == ["Go"]


def test_javascript_does_not_match_java(seed_dir: Path) -> None:
    finder = CandidateSkillFinder.from_csv(seed_dir)

    # "JavaScript" alone must NOT match "Java"
    assert finder.find("Thành thạo JavaScript trong phát triển web.") == ["JavaScript"]

    # When both appear, both are matched
    assert finder.find("Thành thạo Java và JavaScript.") == ["Java", "JavaScript"]


def test_order_by_first_position(seed_dir: Path) -> None:
    finder = CandidateSkillFinder.from_csv(seed_dir)

    res1 = finder.find("Kỹ năng: Python, Java, Postgres")
    assert res1 == ["Python", "Java", "PostgreSQL"]

    res2 = finder.find("Kỹ năng: Java, Python, Postgres")
    assert res2 == ["Java", "Python", "PostgreSQL"]


def test_limit(seed_dir: Path) -> None:
    finder = CandidateSkillFinder.from_csv(seed_dir)
    text = "Kỹ năng: Python, Java, Postgres, React"

    assert finder.find(text, limit=2) == ["Python", "Java"]
    assert finder.find(text, limit=1) == ["Python"]
    assert finder.find(text, limit=0) == []
    assert finder.find(text, limit=-5) == []


def test_deduplication_name_and_alias(seed_dir: Path) -> None:
    finder = CandidateSkillFinder.from_csv(seed_dir)

    # Both React (name) and ReactJS (alias) appear -> deduplicated to ["React"]
    assert finder.find("Tôi dùng React và ReactJS.") == ["React"]
    assert finder.find("Tôi dùng ReactJS và React.") == ["React"]


def test_empty_cv(seed_dir: Path) -> None:
    finder = CandidateSkillFinder.from_csv(seed_dir)

    assert finder.find("") == []
    assert finder.find("   ") == []
    assert finder.find(None) == []  # type: ignore[arg-type]


def test_short_symbols_c_csharp_cpp(seed_dir: Path) -> None:
    finder = CandidateSkillFinder.from_csv(seed_dir)

    # In "C#", "C" must NOT match
    assert finder.find("Lập trình C# cơ bản.") == ["C#"]

    # In "C++", "C" must NOT match
    assert finder.find("Lập trình C++ nâng cao.") == ["C++"]

    # "C/C++" matches both
    assert finder.find("Lập trình C/C++.") == ["C", "C++"]

    # Standalone "C"
    assert finder.find("Lập trình C chuyên sâu.") == ["C"]


def test_soft_skill_not_filtered(seed_dir: Path) -> None:
    finder = CandidateSkillFinder.from_csv(seed_dir)
    assert finder.find("Kỹ năng Communication tốt.") == ["Communication"]


def test_skip_surface_longer_than_40(seed_dir: Path) -> None:
    finder = CandidateSkillFinder.from_csv(seed_dir)
    assert (
        finder.find(
            "Tôi có Skill Name That Is Way Too Long And Exceeds Forty Characters In Total Length."
        )
        == []
    )


def test_performance_5000_chars(seed_dir: Path) -> None:
    finder = CandidateSkillFinder.from_csv(seed_dir)
    text = (
        "Đây là phần mô tả dài trong CV với nhiều từ ngữ thông thường. "
        "Ứng viên có kỹ năng Python và Java, ngoài ra còn biết sử dụng PostgreSQL và ReactJS. "
        "Làm việc tại các công ty lớn không liên quan như Google hay các dự án phức tạp. "
    ) * 30  # ~5,000+ characters
    assert len(text) >= 5000

    start = time.perf_counter()
    res = finder.find(text)
    duration = time.perf_counter() - start

    assert duration < 0.050  # Must run in < 50 ms
    assert "Python" in res
    assert "Java" in res
    assert "PostgreSQL" in res
    assert "React" in res
    assert "Go" not in res
