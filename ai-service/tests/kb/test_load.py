"""Tests for KB loader and validation logic (synthetic data only)."""

from __future__ import annotations

import copy
import csv
import os
from pathlib import Path

import pytest

from kb.load import load, read_seed, validate


@pytest.fixture
def valid_seed_data() -> dict[str, list[dict[str, str]]]:
    """Returns valid synthetic seed data covering all tables."""
    return {
        "categories": [
            {"id": "1", "name": "Programming Language"},
            {"id": "2", "name": "Framework/Library"},
            {"id": "3", "name": "Database"},
        ],
        "skills": [
            {
                "id": "1",
                "name": "Python",
                "category": "Programming Language",
                "reviewed": "true",
            },
            {
                "id": "2",
                "name": "FastAPI",
                "category": "Framework/Library",
                "reviewed": "true",
            },
            {
                "id": "3",
                "name": "PostgreSQL",
                "category": "Database",
                "reviewed": "false",
            },
        ],
        "skill_aliases": [
            {"alias_key": "python", "skill_id": "1", "surface": "Python"},
            {"alias_key": "fastapi", "skill_id": "2", "surface": "FastAPI"},
            {"alias_key": "postgres", "skill_id": "3", "surface": "Postgres"},
        ],
        "skill_edges": [
            {"src_id": "2", "rel": "REQUIRES", "dst_id": "1"},
        ],
        "universities": [
            {
                "id": "1",
                "name": "Hanoi University of Science and Technology",
                "reviewed": "true",
            },
        ],
        "university_aliases": [
            {"alias_key": "hust", "university_id": "1", "surface": "HUST"},
        ],
        "job_titles": [
            {"id": "1", "name": "Backend Developer", "alias_key": "backend_developer"},
        ],
        "job_title_skills": [
            {"job_title_id": "1", "skill_id": "1", "weight": "1.0"},
        ],
        "section_headings": [
            {"heading": "EXPERIENCE", "section": "WORK_EXPERIENCE"},
            {"heading": "SKILLS", "section": "SKILLS"},
        ],
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_seed_dir(target_dir: Path, data: dict[str, list[dict[str, str]]]) -> None:
    for key, rows in data.items():
        _write_csv(target_dir / f"{key}.csv", rows)


def test_read_seed_valid(tmp_path: Path, valid_seed_data: dict[str, list[dict[str, str]]]) -> None:
    _write_seed_dir(tmp_path, valid_seed_data)
    loaded = read_seed(tmp_path)
    assert len(loaded["categories"]) == 3
    assert len(loaded["skills"]) == 3
    assert len(loaded["skill_aliases"]) == 3
    assert len(loaded["skill_edges"]) == 1
    assert len(loaded["universities"]) == 1
    assert len(loaded["university_aliases"]) == 1
    assert len(loaded["job_titles"]) == 1
    assert len(loaded["section_headings"]) == 2


def test_read_seed_missing_required(tmp_path: Path) -> None:
    # Empty dir - missing categories.csv
    with pytest.raises(FileNotFoundError, match="categories.csv"):
        read_seed(tmp_path)

    # Has categories but missing skills.csv
    _write_csv(tmp_path / "categories.csv", [{"id": "1", "name": "Language"}])
    with pytest.raises(FileNotFoundError, match="skills.csv"):
        read_seed(tmp_path)


def test_read_seed_missing_optional(tmp_path: Path) -> None:
    _write_csv(tmp_path / "categories.csv", [{"id": "1", "name": "Language"}])
    _write_csv(
        tmp_path / "skills.csv",
        [{"id": "1", "name": "Python", "category": "Language", "reviewed": "true"}],
    )
    loaded = read_seed(tmp_path)
    assert len(loaded["categories"]) == 1
    assert len(loaded["skills"]) == 1
    assert loaded["skill_aliases"] == []
    assert loaded["skill_edges"] == []
    assert loaded["universities"] == []
    assert loaded["university_aliases"] == []
    assert loaded["job_titles"] == []
    assert loaded["section_headings"] == []


def test_validate_valid_seed(valid_seed_data: dict[str, list[dict[str, str]]]) -> None:
    errors = validate(valid_seed_data)
    assert errors == []


def test_validate_unknown_category(valid_seed_data: dict[str, list[dict[str, str]]]) -> None:
    data = copy.deepcopy(valid_seed_data)
    data["skills"].append(
        {"id": "4", "name": "Rust", "category": "UnknownCat", "reviewed": "true"}
    )
    errors = validate(data)
    assert any("unknown category 'UnknownCat'" in e for e in errors)


def test_validate_duplicate_category(valid_seed_data: dict[str, list[dict[str, str]]]) -> None:
    data = copy.deepcopy(valid_seed_data)
    data["categories"].append({"id": "1", "name": "Another Name"})
    data["categories"].append({"id": "4", "name": "Database"})
    errors = validate(data)
    assert any("Duplicate category id: 1" in e for e in errors)
    assert any("Duplicate category name: 'Database'" in e for e in errors)


def test_validate_duplicate_skill_id_or_name(
    valid_seed_data: dict[str, list[dict[str, str]]],
) -> None:
    data = copy.deepcopy(valid_seed_data)
    data["skills"].append(
        {
            "id": "1",
            "name": "Different Name",
            "category": "Programming Language",
            "reviewed": "true",
        }
    )
    data["skills"].append(
        {"id": "5", "name": "Python", "category": "Programming Language", "reviewed": "true"}
    )
    errors = validate(data)
    assert any("Duplicate skill id: 1" in e for e in errors)
    assert any("Duplicate skill name: 'Python'" in e for e in errors)


def test_validate_duplicate_alias_key(
    valid_seed_data: dict[str, list[dict[str, str]]],
) -> None:
    data = copy.deepcopy(valid_seed_data)
    data["skill_aliases"].append(
        {"alias_key": "python", "skill_id": "2", "surface": "Py"}
    )
    errors = validate(data)
    assert any("Duplicate skill alias_key: 'python'" in e for e in errors)


def test_validate_alias_nonexistent_skill(
    valid_seed_data: dict[str, list[dict[str, str]]],
) -> None:
    data = copy.deepcopy(valid_seed_data)
    data["skill_aliases"].append(
        {"alias_key": "ghost", "skill_id": "999", "surface": "Ghost"}
    )
    errors = validate(data)
    assert any("references non-existent skill_id 999" in e for e in errors)


def test_validate_edge_invalid_rel(
    valid_seed_data: dict[str, list[dict[str, str]]],
) -> None:
    data = copy.deepcopy(valid_seed_data)
    data["skill_edges"].append(
        {"src_id": "1", "rel": "UNKNOWN_REL", "dst_id": "2"}
    )
    errors = validate(data)
    assert any("Invalid skill edge relation 'UNKNOWN_REL'" in e for e in errors)


def test_validate_edge_nonexistent_skill(
    valid_seed_data: dict[str, list[dict[str, str]]],
) -> None:
    data = copy.deepcopy(valid_seed_data)
    data["skill_edges"].append(
        {"src_id": "999", "rel": "PART_OF", "dst_id": "1"}
    )
    errors = validate(data)
    assert any("src_id 999 does not exist" in e for e in errors)


def test_validate_edge_self_loop(
    valid_seed_data: dict[str, list[dict[str, str]]],
) -> None:
    data = copy.deepcopy(valid_seed_data)
    data["skill_edges"].append(
        {"src_id": "1", "rel": "REQUIRES", "dst_id": "1"}
    )
    errors = validate(data)
    assert any("self-loop detected: src_id 1 == dst_id 1" in e for e in errors)


def test_validate_edge_cycle_two_nodes(
    valid_seed_data: dict[str, list[dict[str, str]]],
) -> None:
    data = copy.deepcopy(valid_seed_data)
    data["skill_edges"] = [
        {"src_id": "1", "rel": "PART_OF", "dst_id": "2"},
        {"src_id": "2", "rel": "PART_OF", "dst_id": "1"},
    ]
    errors = validate(data)
    assert any("Cycle detected in relation 'PART_OF'" in e for e in errors)


def test_validate_edge_cycle_three_nodes(
    valid_seed_data: dict[str, list[dict[str, str]]],
) -> None:
    data = copy.deepcopy(valid_seed_data)
    data["skill_edges"] = [
        {"src_id": "1", "rel": "REQUIRES", "dst_id": "2"},
        {"src_id": "2", "rel": "REQUIRES", "dst_id": "3"},
        {"src_id": "3", "rel": "REQUIRES", "dst_id": "1"},
    ]
    errors = validate(data)
    assert any("Cycle detected in relation 'REQUIRES'" in e for e in errors)


def test_validate_edge_different_rels_no_cycle(
    valid_seed_data: dict[str, list[dict[str, str]]],
) -> None:
    data = copy.deepcopy(valid_seed_data)
    data["skill_edges"] = [
        {"src_id": "1", "rel": "PART_OF", "dst_id": "2"},
        {"src_id": "2", "rel": "REQUIRES", "dst_id": "1"},
    ]
    errors = validate(data)
    # Different relations -> not a cycle within either rel
    assert errors == []


def test_validate_university_duplicate_and_aliases(
    valid_seed_data: dict[str, list[dict[str, str]]],
) -> None:
    data = copy.deepcopy(valid_seed_data)
    data["universities"].append(
        {"id": "1", "name": "Another University", "reviewed": "true"}
    )
    data["university_aliases"].append(
        {"alias_key": "hust", "university_id": "1", "surface": "HUST2"}
    )
    data["university_aliases"].append(
        {"alias_key": "unknown", "university_id": "999", "surface": "Unknown"}
    )
    errors = validate(data)
    assert any("Duplicate university id: 1" in e for e in errors)
    assert any("Duplicate university alias_key: 'hust'" in e for e in errors)
    assert any("references non-existent university_id 999" in e for e in errors)


def test_validate_job_title_duplicate_alias_key(
    valid_seed_data: dict[str, list[dict[str, str]]],
) -> None:
    data = copy.deepcopy(valid_seed_data)
    data["job_titles"].append(
        {"id": "2", "name": "Backend Dev Lead", "alias_key": "backend_developer"}
    )
    errors = validate(data)
    assert any("Duplicate job_title alias_key: 'backend_developer'" in e for e in errors)


def test_validate_section_heading_duplicate(
    valid_seed_data: dict[str, list[dict[str, str]]],
) -> None:
    data = copy.deepcopy(valid_seed_data)
    data["section_headings"].append(
        {"heading": "SKILLS", "section": "TECHNICAL_SKILLS"}
    )
    errors = validate(data)
    assert any("Duplicate section_heading heading: 'SKILLS'" in e for e in errors)


def test_load_validation_failure_raises(tmp_path: Path) -> None:
    # Seed with an invalid category
    _write_csv(
        tmp_path / "categories.csv",
        [{"id": "1", "name": "Programming Language"}],
    )
    _write_csv(
        tmp_path / "skills.csv",
        [{"id": "1", "name": "Python", "category": "NonExistent", "reviewed": "true"}],
    )
    schema_path = tmp_path / "001_schema.sql"
    schema_path.write_text("SELECT 1;", encoding="utf-8")

    with pytest.raises(ValueError, match="Seed validation failed"):
        load("postgresql://invalid:invalid@localhost/none", tmp_path, schema_path)


def test_load_persists_provenance(tmp_path, valid_seed_data):
    """The migration runs before inserts and all six knowledge tables retain source."""
    from unittest.mock import MagicMock, patch

    data = copy.deepcopy(valid_seed_data)
    for table in ("skills", "skill_aliases", "skill_edges", "universities", "university_aliases", "job_titles"):
        for row in data[table]:
            row["source"] = "wikidata:Q123"
    _write_seed_dir(tmp_path, data)
    cursor = MagicMock()
    cursor.fetchone.return_value = (0,)
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor
    schema = Path(__file__).resolve().parents[2] / "kb/sql/001_schema.sql"
    with patch("kb.load.psycopg.connect", return_value=connection):
        load("mock", tmp_path, schema)
    assert "ADD COLUMN IF NOT EXISTS source TEXT" in cursor.execute.call_args_list[1].args[0]
    source_tables = set()
    for call in cursor.executemany.call_args_list:
        sql, rows = call.args
        if "source)" in sql:
            source_tables.add(sql.split()[2])
            assert all(r[-1] == "wikidata:Q123" for r in rows)
    assert source_tables == {"skill", "skill_alias", "skill_edge", "university", "university_alias", "job_title"}


@pytest.mark.kb_db
def test_load_idempotent_integration(
    tmp_path: Path, valid_seed_data: dict[str, list[dict[str, str]]]
) -> None:
    dsn = os.environ.get("KB_TEST_DSN")
    if not dsn:
        pytest.skip("KB_TEST_DSN not set (use a separate test database: the test truncates all KB tables)")

    _write_seed_dir(tmp_path, valid_seed_data)
    schema_path = Path(__file__).resolve().parents[2] / "kb" / "sql" / "001_schema.sql"
    assert schema_path.exists(), f"Schema file not found at {schema_path}"

    # Run load 1st time
    counts1 = load(dsn=dsn, seed_dir=tmp_path, schema_path=schema_path)

    # Run load 2nd time
    counts2 = load(dsn=dsn, seed_dir=tmp_path, schema_path=schema_path)

    # Must be identical and positive for populated tables
    assert counts1 == counts2
    assert counts1["category"] == 3
    assert counts1["skill"] == 3
    assert counts1["skill_alias"] == 3
    assert counts1["skill_edge"] == 1
    assert counts1["university"] == 1
    assert counts1["university_alias"] == 1
    assert counts1["job_title"] == 1
    assert counts1["section_heading"] == 2
