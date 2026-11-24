"""Unit tests for KnowledgeBase store and loader."""

from __future__ import annotations

from pathlib import Path
import os

import pytest

from app.kb.store import KnowledgeBase, kb_state, kb_summary, load_kb


@pytest.fixture
def sample_seed_dir(tmp_path: Path) -> Path:
    """Create a temporary seed directory with synthetic CSV data matching read_seed schema."""
    categories_csv = tmp_path / "categories.csv"
    categories_csv.write_text(
        "id,name\n"
        "1,Programming Language\n"
        "2,Framework/Library\n",
        encoding="utf-8",
    )

    skills_csv = tmp_path / "skills.csv"
    skills_csv.write_text(
        "id,name,category,reviewed\n"
        "101,Python,Programming Language,true\n"
        "102,Django,Framework/Library,true\n"
        "103,FastAPI,Framework/Library,false\n",
        encoding="utf-8",
    )

    skill_aliases_csv = tmp_path / "skill_aliases.csv"
    skill_aliases_csv.write_text(
        "alias_key,skill_id,surface\n"
        "python,101,Python\n"
        "django,102,Django\n"
        "fastapi,103,FastAPI\n",
        encoding="utf-8",
    )

    skill_edges_csv = tmp_path / "skill_edges.csv"
    skill_edges_csv.write_text(
        "src_id,rel,dst_id\n"
        "102,REQUIRES,101\n"
        "103,REQUIRES,101\n",
        encoding="utf-8",
    )

    universities_csv = tmp_path / "universities.csv"
    universities_csv.write_text(
        "id,name,reviewed\n"
        "1,Học viện Công nghệ Bưu chính Viễn thông,true\n"
        "2,Đại học Bách Khoa Hà Nội,true\n",
        encoding="utf-8",
    )

    university_aliases_csv = tmp_path / "university_aliases.csv"
    university_aliases_csv.write_text(
        "alias_key,university_id,surface\n"
        "ptit,1,PTIT\n"
        "bach khoa ha noi,2,Bách Khoa Hà Nội\n",
        encoding="utf-8",
    )

    return tmp_path


def test_from_csv_loads_correctly(sample_seed_dir: Path) -> None:
    kb = KnowledgeBase.from_csv(sample_seed_dir)

    assert kb.source == "csv"
    assert len(kb.skills) == 3
    assert kb.skills[101] == ("Python", "Programming Language")
    assert kb.skills[102] == ("Django", "Framework/Library")
    assert kb.skills[103] == ("FastAPI", "Framework/Library")

    assert len(kb.universities) == 2
    assert kb.universities[1] == "Học viện Công nghệ Bưu chính Viễn thông"
    assert kb.universities[2] == "Đại học Bách Khoa Hà Nội"

    assert 102 in kb.edges
    assert kb.edges[102] == [("REQUIRES", 101)]
    assert kb.edges[103] == [("REQUIRES", 101)]

    # Linker is functional
    linked = kb.linker.link("Python")
    assert len(linked) >= 1
    assert linked[0].skill_id == 101


def test_link_school_ptit_by_alias(sample_seed_dir: Path) -> None:
    kb = KnowledgeBase.from_csv(sample_seed_dir)
    res = kb.link_school("PTIT")
    assert res == (1, "Học viện Công nghệ Bưu chính Viễn thông")


def test_link_school_unknown_returns_none(sample_seed_dir: Path) -> None:
    kb = KnowledgeBase.from_csv(sample_seed_dir)
    assert kb.link_school("Trường lạ") is None
    assert kb.link_school("") is None
    assert kb.link_school(None) is None
    assert kb.link_school("   ") is None


def test_load_kb_none_dsn_loads_csv(sample_seed_dir: Path) -> None:
    kb = load_kb(None, sample_seed_dir)
    assert kb is not None
    assert kb.source == "csv"
    assert len(kb.skills) == 3
    assert len(kb.universities) == 2


def test_load_kb_invalid_dsn_fallback_to_csv(sample_seed_dir: Path) -> None:
    kb = load_kb("postgresql://invalid:1/x", sample_seed_dir)
    assert kb is not None
    assert kb.source == "csv"
    assert len(kb.skills) == 3
    assert len(kb.universities) == 2


def test_load_kb_nonexistent_dir_returns_none() -> None:
    kb = load_kb(None, "/không/tồn/tại")
    assert kb is None


def test_kb_summary(sample_seed_dir: Path) -> None:
    assert kb_summary(None) is None

    kb = KnowledgeBase.from_csv(sample_seed_dir)
    summary = kb_summary(kb)
    assert summary == {
        "source": "csv",
        "skills": 3,
        "universities": 2,
    }


def test_kb_state_default() -> None:
    assert "kb" in kb_state
    # default state is None (set during startup)
    assert kb_state["kb"] is None or isinstance(kb_state["kb"], KnowledgeBase)


@pytest.mark.kb_db
def test_from_db_matches_from_csv(sample_seed_dir: Path) -> None:
    """Load the synthetic seed into the TEST database, then both sources must agree."""
    dsn = os.environ.get("KB_TEST_DSN")
    if not dsn:
        pytest.skip("KB_TEST_DSN not set (separate test database; never the real KB)")
    from kb.load import load

    root = Path(__file__).resolve().parents[2]
    load(dsn, str(sample_seed_dir), str(root / "kb" / "sql" / "001_schema.sql"))
    db, csv_kb = KnowledgeBase.from_db(dsn), KnowledgeBase.from_csv(str(sample_seed_dir))
    assert db.source == "postgres" and csv_kb.source == "csv"
    assert db.skills == csv_kb.skills
    assert db.edges == csv_kb.edges
    assert db.school_alias == csv_kb.school_alias
    assert db.universities == csv_kb.universities


def test_link_school_with_parenthesised_abbreviation(sample_seed_dir: Path) -> None:
    kb = KnowledgeBase.from_csv(str(sample_seed_dir))
    plain = kb.link_school("PTIT")
    assert plain is not None
    assert kb.link_school("Some Unknown Name (PTIT)") == plain
    assert kb.link_school("Trường không có (XYZ)") is None


def test_link_school_dash_suffix_abbreviation_only():
    from app.kb.store import KnowledgeBase

    kb = KnowledgeBase.__new__(KnowledgeBase)
    kb.universities = {1: "Học viện Synthetic", 2: "Đại học Mẹ Synthetic"}
    from app.kb.keys import school_key
    kb.school_alias = {school_key("Synthetic Institute"): 1, school_key("SYN"): 1,
                       school_key("ĐHQG Synthetic"): 2}
    assert kb.link_school("Synthetic Institute - SYN") == (1, "Học viện Synthetic")
    assert kb.link_school("Unknown School - SYN") == (1, "Học viện Synthetic")
    # multi-word suffix names a parent university: never linked
    assert kb.link_school("Trường Con Synthetic - ĐHQG Synthetic") is None
