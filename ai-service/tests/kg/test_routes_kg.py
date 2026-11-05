"""Tests for KG enrichment integration in API routes and main service startup."""

from __future__ import annotations

import json
import logging
from typing import Iterator

import pytest

from app.core import config
from app.kb.store import KnowledgeBase, kb_state
from app import main


@pytest.fixture(autouse=True)
def kg_on(monkeypatch) -> None:
    """KG enrichment is on by default; fixture ensures KG_ENABLED is True."""
    monkeypatch.setattr(config, "KG_ENABLED", True)


@pytest.fixture(autouse=True)
def reset_kb_state() -> Iterator[None]:
    """Ensure kb_state['kb'] is cleared after every test."""
    yield
    kb_state["kb"] = None


@pytest.fixture
def fake_kb(tmp_path) -> KnowledgeBase:
    """Create a minimal synthetic KnowledgeBase from temporary CSV files."""
    skills_csv = tmp_path / "skills.csv"
    skills_csv.write_text(
        "id,name,category\n"
        "1,Spring Boot,Backend Framework\n"
        "2,Java,Programming Language\n",
        encoding="utf-8",
    )
    edges_csv = tmp_path / "skill_edges.csv"
    edges_csv.write_text(
        "src_id,rel,dst_id\n"
        "1,REQUIRES,2\n",
        encoding="utf-8",
    )
    unis_csv = tmp_path / "universities.csv"
    unis_csv.write_text(
        "id,name\n"
        "10,Học viện Công nghệ Bưu chính Viễn thông\n",
        encoding="utf-8",
    )
    aliases_csv = tmp_path / "university_aliases.csv"
    aliases_csv.write_text(
        "university_id,alias_key\n"
        "10,ptit\n",
        encoding="utf-8",
    )
    return KnowledgeBase.from_csv(tmp_path)


def test_extract_cv_enriched_success(client, fake_engine, fake_kb: KnowledgeBase) -> None:
    """(1) Profile is enriched with skills_normalized, implied_skills, school_normalized."""
    kb_state["kb"] = fake_kb
    fake_engine.output = json.dumps({
        "skills": ["Spring Boot"],
        "education": [{"school": "PTIT"}],
    })
    cv_text = "Kỹ năng lập trình: Spring Boot. Học vấn: PTIT."

    resp = client.post("/api/v1/extract-cv?include=kg", json={"cv_text": cv_text})
    assert resp.status_code == 200

    data = resp.json()["data"]
    # skills is canonicalized
    assert data["skills"] == ["Spring Boot"]

    # skills_normalized present and canonical
    assert "skills_normalized" in data
    assert len(data["skills_normalized"]) == 1
    assert data["skills_normalized"][0]["id"] == 1
    assert data["skills_normalized"][0]["name"] == "Spring Boot"

    # implied_skills contains Java
    assert "implied_skills" in data
    implied_names = [item["name"] for item in data["implied_skills"]]
    assert "Java" in implied_names
    assert any(item["id"] == 2 for item in data["implied_skills"])

    # education[0].school is canonicalized, and school_normalized mapped
    assert "education" in data
    assert len(data["education"]) >= 1
    assert data["education"][0]["school"] == "Học viện Công nghệ Bưu chính Viễn thông"
    assert data["education"][0]["school_normalized"] == {
        "id": 10,
        "name": "Học viện Công nghệ Bưu chính Viễn thông",
    }


def test_extract_cv_kg_disabled(client, fake_engine, fake_kb: KnowledgeBase, monkeypatch) -> None:
    """(2) KG_ENABLED=False -> skills_normalized and implied_skills not present."""
    monkeypatch.setattr(config, "KG_ENABLED", False)
    kb_state["kb"] = fake_kb
    fake_engine.output = json.dumps({
        "skills": ["Spring Boot"],
        "education": [{"school": "PTIT"}],
    })
    cv_text = "Kỹ năng Spring Boot, tốt nghiệp PTIT."

    resp = client.post("/api/v1/extract-cv?include=kg", json={"cv_text": cv_text})
    assert resp.status_code == 200

    data = resp.json()["data"]
    assert "skills_normalized" not in data
    assert "implied_skills" not in data


def test_extract_cv_kb_state_none(client, fake_engine) -> None:
    """(3) kb_state['kb']=None -> no enrichment keys, still 200."""
    kb_state["kb"] = None
    fake_engine.output = json.dumps({
        "skills": ["Spring Boot"],
        "education": [{"school": "PTIT"}],
    })
    cv_text = "Kỹ năng Spring Boot, tốt nghiệp PTIT."

    resp = client.post("/api/v1/extract-cv?include=kg", json={"cv_text": cv_text})
    assert resp.status_code == 200

    data = resp.json()["data"]
    assert "skills_normalized" not in data
    assert "implied_skills" not in data


def test_extract_cv_enrich_raises_handled(
    client, fake_engine, fake_kb: KnowledgeBase, monkeypatch
) -> None:
    """(4) enrich raising RuntimeError returns 200 without skills_normalized."""
    kb_state["kb"] = fake_kb
    fake_engine.output = json.dumps({
        "skills": ["Spring Boot"],
        "education": [{"school": "PTIT"}],
    })
    cv_text = "Kỹ năng Spring Boot, tốt nghiệp PTIT."

    def _boom(*_args, **_kwargs):
        raise RuntimeError("simulated enrich error")

    monkeypatch.setattr("app.api.routes.enrich", _boom)

    resp = client.post("/api/v1/extract-cv?include=kg", json={"cv_text": cv_text})
    assert resp.status_code == 200

    data = resp.json()["data"]
    assert "skills_normalized" not in data
    assert "implied_skills" not in data
    assert data["skills"] == ["Spring Boot"]


def test_health_with_and_without_kb(client, fake_engine, fake_kb: KnowledgeBase) -> None:
    """(5) /health returns source/skills/universities when KB is set, and None when not."""
    kb_state["kb"] = fake_kb
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("kb") == {
        "source": "csv",
        "skills": 2,
        "universities": 1,
    }

    kb_state["kb"] = None
    resp_none = client.get("/health")
    assert resp_none.status_code == 200
    assert resp_none.json().get("kb") is None


def test_logging_counts_only_no_raw_skills(
    client, fake_engine, fake_kb: KnowledgeBase, caplog: pytest.LogCaptureFixture
) -> None:
    """(6) caplog contains no raw skill 'Spring Boot' in the 'kg' log entry."""
    kb_state["kb"] = fake_kb
    fake_engine.output = json.dumps({
        "skills": ["Spring Boot"],
        "education": [{"school": "PTIT"}],
    })
    cv_text = "Kỹ năng Spring Boot, tốt nghiệp PTIT."

    with caplog.at_level(logging.INFO):
        resp = client.post("/api/v1/extract-cv?include=kg", json={"cv_text": cv_text})

    assert resp.status_code == 200

    kg_records = [r for r in caplog.records if " kg " in r.getMessage()]
    assert len(kg_records) >= 1
    for r in kg_records:
        msg = r.getMessage()
        assert "Spring Boot" not in msg
        assert "Java" not in msg


def test_main_startup_kg_enabled(monkeypatch) -> None:
    """startup() calls load_kb when KG_ENABLED=True."""
    calls: list[tuple] = []

    def _fake_load_kb(dsn, seed_dir):
        calls.append((dsn, seed_dir))
        return "synthetic_kb"

    monkeypatch.setattr("app.main.load_kb", _fake_load_kb)
    monkeypatch.setattr("app.main.load_model", lambda: None)
    monkeypatch.setattr(config, "KG_ENABLED", True)

    main.startup()
    assert kb_state["kb"] == "synthetic_kb"
    assert len(calls) == 1


def test_main_startup_kg_disabled(monkeypatch) -> None:
    """startup() skips load_kb when KG_ENABLED=False."""
    calls: list[tuple] = []

    def _fake_load_kb(dsn, seed_dir):
        calls.append((dsn, seed_dir))
        return "synthetic_kb"

    monkeypatch.setattr("app.main.load_kb", _fake_load_kb)
    monkeypatch.setattr("app.main.load_model", lambda: None)
    monkeypatch.setattr(config, "KG_ENABLED", False)

    main.startup()
    assert kb_state["kb"] is None
    assert len(calls) == 0
