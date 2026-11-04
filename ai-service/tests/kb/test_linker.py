"""Unit tests for KB skill/school keys and SkillLinker entity linking."""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.kb.keys import school_key, skill_key
from app.kb.linker import Link, SkillLinker


# ---------------------------------------------------------------------------
# Tests for Keys
# ---------------------------------------------------------------------------


def test_skill_key_examples() -> None:
    assert skill_key("ReactJS") == "react"
    assert skill_key("React.js") == "react"
    assert skill_key("Node JS") == "node"
    assert skill_key("Next.js") == "next"
    assert skill_key("Tailwind-CSS") == "tailwindcss"
    assert skill_key("C#") == "c#"
    assert skill_key("C++") == "c++"
    assert skill_key("CI/CD") == "cicd"
    assert skill_key("JS") == "js"
    assert skill_key("Vue.js") == "vue"


def test_skill_key_edge_cases() -> None:
    assert skill_key(None) == ""
    assert skill_key("") == ""
    assert skill_key("   ") == ""
    assert skill_key("RxJS") == "rx"


def test_school_key_examples() -> None:
    assert (
        school_key("Trường Đại học Bách khoa Hà Nội") == "bach khoa ha noi"
    )
    assert (
        school_key("Học viện Công nghệ Bưu chính Viễn thông")
        == "cong nghe buu chinh vien thong"
    )
    assert (
        school_key("University of Engineering and Technology")
        == "engineering and technology"
    )
    assert school_key("Stanford University") == "stanford"
    assert school_key("The University of Tokyo") == "tokyo"


def test_school_key_edge_cases() -> None:
    assert school_key(None) == ""
    assert school_key("") == ""
    assert school_key("   ") == ""


# ---------------------------------------------------------------------------
# Fixture & Synthetic Seed Data
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_seed_dir(tmp_path: Path) -> Path:
    """Create synthetic skills.csv and skill_aliases.csv for unit testing."""
    skills_csv = tmp_path / "skills.csv"
    with skills_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "category", "reviewed"])
        writer.writerow([1, "React", "Frontend", "true"])
        writer.writerow([2, "Tailwind CSS", "Frontend", "true"])
        writer.writerow([3, "PostgreSQL", "Database", "true"])
        writer.writerow([4, "Java", "Backend", "true"])
        writer.writerow([5, "Spring Boot", "Backend", "true"])
        writer.writerow([6, "Git", "Tool", "true"])
        writer.writerow([7, "GitHub", "Tool", "true"])
        writer.writerow([8, "CI-CD", "DevOps", "true"])
        writer.writerow([9, "C", "Programming Language", "true"])
        writer.writerow([10, "C#", "Programming Language", "true"])
        writer.writerow([11, "C++", "Programming Language", "true"])
        writer.writerow([12, "Go", "Programming Language", "true"])

    aliases_csv = tmp_path / "skill_aliases.csv"
    with aliases_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["alias_key", "skill_id", "surface"])
        writer.writerow(["react", 1, "React"])
        writer.writerow(["reactjs", 1, "ReactJS"])
        writer.writerow(["tailwindcss", 2, "Tailwind CSS"])
        writer.writerow(["postgresql", 3, "PostgreSQL"])
        writer.writerow(["postgres", 3, "Postgres"])
        writer.writerow(["java", 4, "Java"])
        writer.writerow(["springboot", 5, "Spring Boot"])
        writer.writerow(["git", 6, "Git"])
        writer.writerow(["github", 7, "GitHub"])
        writer.writerow(["cicd", 8, "CI-CD"])
        writer.writerow(["c", 9, "C"])
        writer.writerow(["c#", 10, "C#"])
        writer.writerow(["c++", 11, "C++"])
        writer.writerow(["go", 12, "Go"])

    return tmp_path


@pytest.fixture
def linker(synthetic_seed_dir: Path) -> SkillLinker:
    return SkillLinker.from_csv(synthetic_seed_dir)


# ---------------------------------------------------------------------------
# Tests for SkillLinker Matching Rules
# ---------------------------------------------------------------------------


def test_react_variants_share_same_id(linker: SkillLinker) -> None:
    l_exact = linker.link("react")
    assert len(l_exact) == 1
    assert l_exact[0].skill_id == 1
    assert l_exact[0].method == "exact"
    assert l_exact[0].score == 100.0

    l_js1 = linker.link("ReactJS")
    assert len(l_js1) == 1
    assert l_js1[0].skill_id == 1

    l_js2 = linker.link("React.js")
    assert len(l_js2) == 1
    assert l_js2[0].skill_id == 1


def test_tailwind_css_normalized(linker: SkillLinker) -> None:
    links = linker.link("Tailwind-CSS")
    assert len(links) == 1
    assert links[0].method == "normalized"
    assert links[0].skill_id == 2
    assert links[0].name == "Tailwind CSS"
    assert links[0].category == "Frontend"
    assert links[0].score == 100.0


def test_postgress_fuzzy(linker: SkillLinker) -> None:
    links = linker.link("Postgress")
    assert len(links) == 1
    assert links[0].method == "fuzzy"
    assert links[0].score >= 90.0
    assert links[0].skill_id == 3
    assert links[0].name == "PostgreSQL"
    assert links[0].category == "Database"


def test_split_java_and_spring_boot(linker: SkillLinker) -> None:
    links = linker.link("Java & Spring Boot")
    assert len(links) == 2
    assert links[0].name == "Java"
    assert links[0].method == "split"
    assert links[0].score == 100.0
    assert links[1].name == "Spring Boot"
    assert links[1].method == "split"
    assert links[1].score == 100.0


def test_split_git_slash_github(linker: SkillLinker) -> None:
    links = linker.link("Git/GitHub")
    assert len(links) == 2
    assert links[0].name == "Git"
    assert links[0].method == "split"
    assert links[1].name == "GitHub"
    assert links[1].method == "split"


def test_ci_cd_normalized_not_split(linker: SkillLinker) -> None:
    links = linker.link("CI/CD")
    assert len(links) == 1
    assert links[0].method == "normalized"
    assert links[0].skill_id == 8
    assert links[0].name == "CI-CD"


def test_go_exact(linker: SkillLinker) -> None:
    links = linker.link("Go")
    assert len(links) == 1
    assert links[0].method == "exact"
    assert links[0].skill_id == 12
    assert links[0].name == "Go"


def test_gooo_len_4_unlinked_no_false_positive(linker: SkillLinker) -> None:
    links = linker.link("Gooo")
    assert len(links) == 1
    assert links[0].method == "unlinked"
    assert links[0].skill_id is None
    assert links[0].score == 0.0


def test_soft_skill_sentence_unlinked(linker: SkillLinker) -> None:
    raw = "Kỹ năng giao tiếp tốt với khách hàng"
    links = linker.link(raw)
    assert len(links) == 1
    assert links[0].method == "unlinked"
    assert links[0].skill_id is None
    assert links[0].score == 0.0


def test_backend_group_label_cleaning(linker: SkillLinker) -> None:
    links = linker.link("Backend: Java, Go")
    assert len(links) == 2
    assert [l.name for l in links] == ["Java", "Go"]
    assert [l.skill_id for l in links] == [4, 12]


def test_link_many_dedupe(linker: SkillLinker) -> None:
    raws = ["Java", "Backend: Java, Go", "Kỹ năng mềm", "Java"]
    links = linker.link_many(raws)
    linked_names = [l.name for l in links if l.skill_id is not None]
    assert linked_names == ["Java", "Go"]

    unlinked = [l for l in links if l.skill_id is None]
    assert len(unlinked) == 1
    assert unlinked[0].raw == "Kỹ năng mềm"


def test_partial_split_one_linked_one_unlinked(linker: SkillLinker) -> None:
    links = linker.link("Java / UnknownTechX")
    assert len(links) == 2
    assert links[0].name == "Java"
    assert links[0].method == "split"
    assert links[1].name is None
    assert links[1].method == "unlinked"
    assert links[1].skill_id is None


def test_empty_and_whitespace_input(linker: SkillLinker) -> None:
    assert linker.link("") == []
    assert linker.link("   ") == []


def test_c_and_variants(linker: SkillLinker) -> None:
    l_c = linker.link("C")
    assert len(l_c) == 1
    assert l_c[0].name == "C"

    l_csharp = linker.link("C#")
    assert len(l_csharp) == 1
    assert l_csharp[0].name == "C#"

    l_cpp = linker.link("C++")
    assert len(l_cpp) == 1
    assert l_cpp[0].name == "C++"


# ---------------------------------------------------------------------------
# Test SkillLinker.from_db Query Contract
# ---------------------------------------------------------------------------


def test_from_db_query_contract() -> None:
    mock_cursor = MagicMock()
    mock_cursor.fetchall.side_effect = [
        [(1, "React", "Frontend"), (2, "Java", "Backend")],
        [("react", 1, "React"), ("java", 2, "Java")],
    ]

    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    mock_psycopg = MagicMock()
    mock_psycopg.connect.return_value = mock_conn

    with patch.dict("sys.modules", {"psycopg": mock_psycopg}):
        db_linker = SkillLinker.from_db("postgresql://kb:test@localhost:5433/recruit_kb")
        assert len(db_linker.skills) == 2
        assert db_linker.skills[1] == ("React", "Frontend")
        assert db_linker.skills[2] == ("Java", "Backend")

    executed_queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
    assert any("SELECT s.id, s.name, c.name FROM skill s JOIN category c" in q for q in executed_queries)
    assert any("SELECT alias_key, skill_id, surface FROM skill_alias" in q for q in executed_queries)
