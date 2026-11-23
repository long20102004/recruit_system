"""Unit tests for Neo4j KnowledgeBase loader, store, and fallbacks using synthetic in-memory fakes."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import patch

# Allow tests to run even if neo4j package is not yet installed in local environment
try:
    import neo4j
except ImportError:
    neo4j = ModuleType("neo4j")
    neo4j.GraphDatabase = ModuleType("GraphDatabase")
    sys.modules["neo4j"] = neo4j

import pytest

from app.kb.store import KnowledgeBase, load_kb
from kb.neo4j_load import (
    CONSTRAINTS,
    create_constraints,
    get_graph_counts,
    load_kb1_and_merge,
    load_kb2,
    load_to_neo4j,
    reset_database,
)


class FakeRecord(dict):
    """Duck-typed neo4j.Record supporting key access and .get()."""

    def __getitem__(self, key: str):
        return super().__getitem__(key)

    def get(self, key: str, default=None):
        return super().get(key, default)


class FakeResult:
    def __init__(self, records: list[dict]):
        self._records = [FakeRecord(r) for r in records]

    def __iter__(self):
        return iter(self._records)

    def single(self):
        return self._records[0] if self._records else None


class FakeSession:
    def __init__(self, query_responses: dict[str, list[dict]] | None = None):
        self.responses = query_responses or {}
        self.recorded_queries: list[tuple[str, dict]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def run(self, query: str, **kwargs):
        self.recorded_queries.append((query.strip(), kwargs))
        query_text = query.strip()
        for key, rows in self.responses.items():
            if key in query_text:
                return FakeResult(rows)
        # Default fallback for count queries
        return FakeResult([{"c": 1}])


class FakeDriver:
    def __init__(self, session: FakeSession):
        self._session = session
        self.closed = False

    def session(self):
        return self._session

    def close(self):
        self.closed = True


@pytest.fixture
def sample_neo4j_records() -> dict[str, list[dict]]:
    """Synthetic records mimicking Neo4j graph tables for from_neo4j."""
    return {
        "MATCH (s:Skill)": [
            {"id": 1, "name": "Python", "category": "Programming Language"},
            {"id": 2, "name": "Git", "category": "Tool"},
            {"id": 3, "name": "GitHub", "category": "Tool"},
        ],
        "MATCH (a:Alias)-[:ALIAS_OF]->(s:Skill)": [
            {"key": "python", "surface": "Python", "skill_id": 1},
            {"key": "py", "surface": "Py", "skill_id": 1},
            {"key": "git", "surface": "Git", "skill_id": 2},
            {"key": "github", "surface": "GitHub", "skill_id": 3},
        ],
        "MATCH (src:Skill)-[r:REQUIRES|PART_OF]->(dst:Skill)": [
            {"src_id": 3, "rel": "REQUIRES", "dst_id": 2},
        ],
        "MATCH (a:Skill)-[r:RELATED_TO]-(b:Skill)": [
            {"a_id": 2, "b_id": 3, "weight": 7.0},
        ],
        "MATCH (u:University)": [
            {"id": 187, "name": "Học viện Công nghệ Bưu chính Viễn thông"},
        ],
        "MATCH (ua:UniversityAlias)-[:ALIAS_OF]->(u:University)": [
            {"key": "ptit", "university_id": 187},
        ],
    }


@pytest.fixture
def sample_seed_files(tmp_path: Path) -> Path:
    """Create minimal synthetic seed CSV files."""
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()

    (seed_dir / "categories.csv").write_text(
        "id,name,source\n"
        "1,Programming Language,src1\n"
        "2,Tool,src2\n",
        encoding="utf-8",
    )
    (seed_dir / "skills.csv").write_text(
        "id,name,category,source,source_id\n"
        "1,Python,Programming Language,src1,Q1\n"
        "2,Git,Tool,src2,Q2\n"
        "3,GitHub,Tool,src2,Q3\n",
        encoding="utf-8",
    )
    (seed_dir / "skill_aliases.csv").write_text(
        "alias_key,skill_id,surface,source\n"
        "python,1,Python,src1\n"
        "git,2,Git,src2\n"
        "github,3,GitHub,src2\n",
        encoding="utf-8",
    )
    (seed_dir / "skill_edges.csv").write_text(
        "src_id,rel,dst_id,source\n"
        "3,REQUIRES,2,src2\n",
        encoding="utf-8",
    )
    (seed_dir / "universities.csv").write_text(
        "id,name,source\n"
        "187,Học viện Công nghệ Bưu chính Viễn thông,wiki\n",
        encoding="utf-8",
    )
    (seed_dir / "university_aliases.csv").write_text(
        "alias_key,university_id,source\n"
        "ptit,187,wiki\n",
        encoding="utf-8",
    )
    (seed_dir / "job_titles.csv").write_text(
        "id,name,alias_key,source\n"
        "1,Software Engineer,software engineer,esco\n",
        encoding="utf-8",
    )
    return seed_dir


@pytest.fixture
def sample_books_json(tmp_path: Path) -> Path:
    """Create minimal synthetic kb1_books.json."""
    books_file = tmp_path / "kb1_books.json"
    content = {
        "books": [
            {
                "id": "progit",
                "title": "Pro Git",
                "authors": ["Scott Chacon", "Ben Straub"],
                "edition": "2",
                "licence": "CC BY-NC-SA 3.0",
                "url": "https://git-scm.com/book/en/v2",
                "sha256": "abcdef123456",
                "sections": [
                    {
                        "id": "progit:1",
                        "title": "Getting Started",
                        "level": 1,
                        "page": 1,
                        "parent": None,
                        "mentions": {"Git": 15},
                    },
                    {
                        "id": "progit:1.1",
                        "title": "About Git",
                        "level": 2,
                        "page": 2,
                        "parent": "progit:1",
                        "mentions": {"Git": 20, "GitHub": 5},
                    },
                ],
            }
        ],
        "related": [
            {"a": "Git", "b": "GitHub", "sections": 7, "source": "progit"}
        ],
    }
    books_file.write_text(json.dumps(content), encoding="utf-8")
    return books_file


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


def test_from_neo4j_constructs_valid_knowledgebase(sample_neo4j_records: dict) -> None:
    """KnowledgeBase.from_neo4j reads nodes and edges, instantiating linker, related, and school resolver."""
    fake_session = FakeSession(sample_neo4j_records)
    fake_driver = FakeDriver(fake_session)

    with patch("neo4j.GraphDatabase.driver", return_value=fake_driver):
        kb = KnowledgeBase.from_neo4j("bolt://localhost:7687", "neo4j", "testpass")

    assert fake_driver.closed is True
    assert kb.source == "neo4j"

    # Skills
    assert len(kb.skills) == 3
    assert kb.skills[1] == ("Python", "Programming Language")
    assert kb.skills[2] == ("Git", "Tool")
    assert kb.skills[3] == ("GitHub", "Tool")

    # Edges
    assert kb.edges[3] == [("REQUIRES", 2)]

    # Related (symmetrical)
    assert 2 in kb.related
    assert kb.related[2] == [(3, 7.0)]
    assert 3 in kb.related
    assert kb.related[3] == [(2, 7.0)]

    # Universities & Aliases
    assert kb.universities[187] == "Học viện Công nghệ Bưu chính Viễn thông"
    assert kb.school_alias["ptit"] == 187
    assert kb.link_school("PTIT") == (187, "Học viện Công nghệ Bưu chính Viễn thông")
    assert kb.link_school("Học viện Công nghệ Bưu chính Viễn thông") == (
        187,
        "Học viện Công nghệ Bưu chính Viễn thông",
    )

    # Linker
    linked = kb.linker.link("Python")
    assert len(linked) == 1
    assert linked[0].skill_id == 1
    assert linked[0].name == "Python"


def test_neo4j_load_generates_expected_queries_and_batches(
    sample_seed_files: Path, sample_books_json: Path
) -> None:
    """neo4j_load issues correct UNWIND queries, constraints, reset, and batch parameters."""
    session = FakeSession()

    # 1. Reset
    reset_database(session)
    assert any("MATCH (n) DETACH DELETE n" in q[0] for q in session.recorded_queries)

    # 2. Constraints
    create_constraints(session)
    constraint_queries = [q[0] for q in session.recorded_queries if "CREATE CONSTRAINT" in q[0]]
    assert len(constraint_queries) == len(CONSTRAINTS)
    assert any("FOR (n:Skill) REQUIRE n.id IS UNIQUE" in q for q in constraint_queries)
    assert any("FOR (n:Book) REQUIRE n.id IS UNIQUE" in q for q in constraint_queries)

    # 3. Load KB2
    kb2_stats = load_kb2(session, sample_seed_files)
    assert kb2_stats["categories"] == 2
    assert kb2_stats["skills"] == 3
    assert kb2_stats["aliases"] == 3
    assert kb2_stats["edges_requires"] == 1
    assert kb2_stats["universities"] == 1
    assert kb2_stats["university_aliases"] == 1
    assert kb2_stats["job_titles"] == 1

    # Verify UNWIND queries contain KB2 label
    kb2_queries = [q[0] for q in session.recorded_queries if "SET s:KB2" in q[0] or "SET c:KB2" in q[0]]
    assert len(kb2_queries) >= 1

    # 4. Load KB1 and merge
    kb1_stats = load_kb1_and_merge(session, sample_books_json, sample_seed_files)
    assert kb1_stats["books"] == 1
    assert kb1_stats["sections"] == 2
    assert kb1_stats["mentions"] >= 2
    assert kb1_stats["related"] == 1

    # Check ABOUT relation and RELATED_TO relation queries
    all_queries = [q[0] for q in session.recorded_queries]
    assert any("RELATED_TO" in q for q in all_queries)
    assert any("HAS_SECTION" in q for q in all_queries)
    assert any("MENTIONS" in q for q in all_queries)


def test_load_to_neo4j_runner(sample_seed_files: Path, sample_books_json: Path) -> None:
    """load_to_neo4j coordinates reset, constraints, KB2, KB1 and returns graph counts."""
    session = FakeSession()
    driver = FakeDriver(session)

    with patch("neo4j.GraphDatabase.driver", return_value=driver):
        counts = load_to_neo4j(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="secret_password",
            seed_dir=sample_seed_files,
            books_file=sample_books_json,
            reset=True,
        )

    assert "nodes" in counts
    assert "relationships" in counts
    assert driver.closed is True


def test_load_kb_fallback_order(sample_seed_files: Path) -> None:
    """load_kb follows Neo4j -> Postgres -> CSV order, gracefully falling back on errors."""
    # 1. Neo4j raises error -> falls back to CSV
    with patch(
        "app.kb.store.KnowledgeBase.from_neo4j",
        side_effect=ConnectionRefusedError("Neo4j down"),
    ):
        kb = load_kb(
            dsn=None,
            seed_dir=sample_seed_files,
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="pwd",
        )
        assert kb is not None
        assert kb.source == "csv"
        assert len(kb.skills) == 3

    # 2. Neo4j and Postgres both fail -> falls back to CSV
    with patch(
        "app.kb.store.KnowledgeBase.from_neo4j",
        side_effect=RuntimeError("Neo4j error"),
    ), patch(
        "app.kb.store.KnowledgeBase.from_db",
        side_effect=RuntimeError("PG error"),
    ):
        kb = load_kb(
            dsn="postgresql://invalid:5432/db",
            seed_dir=sample_seed_files,
            neo4j_uri="bolt://localhost:7687",
        )
        assert kb is not None
        assert kb.source == "csv"

    # 3. Neo4j succeeds -> returns Neo4j KB directly
    fake_kb = KnowledgeBase(
        source="neo4j",
        linker=kb.linker,
        skills=kb.skills,
        edges=kb.edges,
        school_alias=kb.school_alias,
        universities=kb.universities,
        related={2: [(3, 7.0)]},
    )
    with patch("app.kb.store.KnowledgeBase.from_neo4j", return_value=fake_kb):
        kb_neo = load_kb(
            dsn="postgresql://invalid:5432/db",
            seed_dir=sample_seed_files,
            neo4j_uri="bolt://localhost:7687",
        )
        assert kb_neo is not None
        assert kb_neo.source == "neo4j"
        assert kb_neo.related == {2: [(3, 7.0)]}
