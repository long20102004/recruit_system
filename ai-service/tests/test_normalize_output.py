"""Tests for profile normalisation with KB and include query param in API routes."""

from __future__ import annotations

import copy
import json
from typing import Iterator

import pytest

from app.core import config
from app.kb.normalize import normalize_profile_with_kb
from app.kb.store import KnowledgeBase, kb_state

CV_TEXT = "SYNTHETIC CV\nReactJS, Postgress, UnknownSkill\nPTIT\n"


@pytest.fixture(autouse=True)
def reset_kb_state() -> Iterator[None]:
    """Ensure kb_state['kb'] is cleared after every test."""
    yield
    kb_state["kb"] = None


@pytest.fixture
def fake_kb(tmp_path) -> KnowledgeBase:
    """Create a minimal synthetic KnowledgeBase with skills, aliases, edges, universities."""
    skills_csv = tmp_path / "skills.csv"
    skills_csv.write_text(
        "id,name,category\n"
        "1,React,Frontend\n"
        "2,PostgreSQL,Database\n"
        "3,Python,Language\n",
        encoding="utf-8",
    )
    aliases_csv = tmp_path / "skill_aliases.csv"
    aliases_csv.write_text(
        "alias_key,skill_id,surface\n"
        "reactjs,1,ReactJS\n"
        "postgres,2,Postgres\n",
        encoding="utf-8",
    )
    edges_csv = tmp_path / "skill_edges.csv"
    edges_csv.write_text(
        "src_id,rel,dst_id\n"
        "1,REQUIRES,3\n",
        encoding="utf-8",
    )
    unis_csv = tmp_path / "universities.csv"
    unis_csv.write_text(
        "id,name\n"
        "10,Học viện Công nghệ Bưu chính Viễn thông\n",
        encoding="utf-8",
    )
    uni_alias_csv = tmp_path / "university_aliases.csv"
    uni_alias_csv.write_text(
        "university_id,alias_key\n"
        "10,ptit\n",
        encoding="utf-8",
    )
    return KnowledgeBase.from_csv(tmp_path)


# =============================================================================
# Unit tests for normalize_profile_with_kb
# =============================================================================


def test_normalize_profile_with_kb_skills(fake_kb: KnowledgeBase) -> None:
    """Skills are canonicalised, fuzzy-matched, unlinked kept, and duplicates removed."""
    profile = {
        "personal_info": {"full_name": "Synthetic Candidate"},
        "skills": ["ReactJS", "Postgress", "UnknownSkill", "react", "React"],
    }
    original_copy = copy.deepcopy(profile)

    res = normalize_profile_with_kb(profile, fake_kb)

    # Pure function: does not mutate profile
    assert profile == original_copy

    # ReactJS -> React; Postgress -> PostgreSQL via fuzzy; UnknownSkill stays;
    # 'react' and 'React' deduplicated (casefold, keep first)
    assert res["skills"] == ["React", "PostgreSQL", "UnknownSkill"]
    assert res["personal_info"] == {"full_name": "Synthetic Candidate"}


def test_normalize_profile_with_kb_projects_tech_stack(fake_kb: KnowledgeBase) -> None:
    """personal_projects[].tech_stack normalised and deduped."""
    profile = {
        "personal_projects": [
            {
                "name": "Project Alpha",
                "tech_stack": ["ReactJS", "Postgress", "react", "CustomLib"],
            }
        ]
    }
    res = normalize_profile_with_kb(profile, fake_kb)
    assert res["personal_projects"][0]["tech_stack"] == ["React", "PostgreSQL", "CustomLib"]


def test_normalize_profile_with_kb_education_school(fake_kb: KnowledgeBase) -> None:
    """education[].school mapped to canonical official university name."""
    profile = {
        "education": [
            {"school": "PTIT", "degree": "Bachelor"},
            {"school": "Unknown College", "degree": "Master"},
        ]
    }
    res = normalize_profile_with_kb(profile, fake_kb)
    assert res["education"][0]["school"] == "Học viện Công nghệ Bưu chính Viễn thông"
    assert res["education"][1]["school"] == "Unknown College"


def test_normalize_profile_with_kb_none_or_missing_linker() -> None:
    """kb is None or incomplete -> return copy of profile unchanged."""
    profile = {
        "skills": ["ReactJS"],
        "education": [{"school": "PTIT"}],
    }

    # kb is None
    res_none = normalize_profile_with_kb(profile, None)
    assert res_none == profile
    assert res_none is not profile

    # kb lacks linker or link_school
    class DummyKB:
        pass

    res_dummy = normalize_profile_with_kb(profile, DummyKB())
    assert res_dummy == profile


# =============================================================================
# API integration tests for POST /api/v1/extract-cv
# =============================================================================


def test_api_extract_cv_default_hidden_kg_normalized_output(
    client, fake_engine, fake_kb: KnowledgeBase
) -> None:
    """Default output has normalised CV fields; KG and raw fields are hidden."""
    kb_state["kb"] = fake_kb
    fake_engine.output = json.dumps({
        "personal_info": {"full_name": "Synthetic Candidate"},
        "skills": ["ReactJS", "Postgress", "UnknownSkill"],
        "education": [{"school": "PTIT"}],
    })

    resp = client.post("/api/v1/extract-cv", json={"cv_text": CV_TEXT})
    assert resp.status_code == 200

    data = resp.json()["data"]

    # Normalised CV fields
    assert data["skills"] == ["React", "PostgreSQL", "UnknownSkill"]
    assert data["education"][0]["school"] == "Học viện Công nghệ Bưu chính Viễn thông"

    # KG enrichment fields must be absent
    for k in ("skills_normalized", "implied_skills", "skills_detected", "flags", "raw_profile"):
        assert k not in data
    assert "school_normalized" not in data["education"][0]


def test_api_extract_cv_include_kg(client, fake_engine, fake_kb: KnowledgeBase) -> None:
    """include=kg adds skills_normalized, implied_skills, skills_detected, flags, school_normalized."""
    kb_state["kb"] = fake_kb
    fake_engine.output = json.dumps({
        "personal_info": {"full_name": "Synthetic Candidate"},
        "skills": ["ReactJS"],
        "education": [{"school": "PTIT"}],
    })

    resp = client.post("/api/v1/extract-cv?include=kg", json={"cv_text": CV_TEXT})
    assert resp.status_code == 200

    data = resp.json()["data"]
    # Base CV fields still normalised
    assert data["skills"] == ["React"]
    assert data["education"][0]["school"] == "Học viện Công nghệ Bưu chính Viễn thông"

    # KG fields present
    assert "skills_normalized" in data
    assert len(data["skills_normalized"]) == 1
    assert data["skills_normalized"][0]["id"] == 1
    assert data["skills_normalized"][0]["name"] == "React"

    assert "implied_skills" in data
    assert any(s["name"] == "Python" for s in data["implied_skills"])

    assert "skills_detected" in data
    assert "flags" in data
    assert data["education"][0]["school_normalized"] == {
        "id": 10,
        "name": "Học viện Công nghệ Bưu chính Viễn thông",
    }

    # raw_profile still absent
    assert "raw_profile" not in data


def test_api_extract_cv_include_raw(client, fake_engine, fake_kb: KnowledgeBase) -> None:
    """include=raw adds raw_profile with grounded model values before normalisation."""
    kb_state["kb"] = fake_kb
    fake_engine.output = json.dumps({
        "personal_info": {"full_name": "Synthetic Candidate"},
        "skills": ["ReactJS"],
        "education": [{"school": "PTIT"}],
    })

    resp = client.post("/api/v1/extract-cv?include=raw", json={"cv_text": CV_TEXT})
    assert resp.status_code == 200

    data = resp.json()["data"]
    assert data["skills"] == ["React"]

    # raw_profile is present and holds original grounded values
    assert "raw_profile" in data
    raw = data["raw_profile"]
    assert raw["skills"] == ["ReactJS"]
    assert raw["education"][0]["school"] == "PTIT"

    # KG enrichment fields absent
    for k in ("skills_normalized", "implied_skills", "skills_detected", "flags"):
        assert k not in data
    assert "school_normalized" not in data["education"][0]


def test_api_extract_cv_include_kg_and_raw(
    client, fake_engine, fake_kb: KnowledgeBase
) -> None:
    """include=kg,raw contains both KG fields and raw_profile."""
    kb_state["kb"] = fake_kb
    fake_engine.output = json.dumps({
        "personal_info": {"full_name": "Synthetic Candidate"},
        "skills": ["ReactJS"],
        "education": [{"school": "PTIT"}],
    })

    resp = client.post("/api/v1/extract-cv?include=kg,raw", json={"cv_text": CV_TEXT})
    assert resp.status_code == 200

    data = resp.json()["data"]
    assert data["skills"] == ["React"]
    assert "skills_normalized" in data
    assert "implied_skills" in data
    assert "skills_detected" in data
    assert "flags" in data
    assert "raw_profile" in data
    assert data["education"][0]["school_normalized"] == {
        "id": 10,
        "name": "Học viện Công nghệ Bưu chính Viễn thông",
    }


def test_api_extract_cv_include_invalid_param(client, fake_engine) -> None:
    """Unknown include value returns HTTP 400 with 'include chỉ nhận kg, raw'."""
    resp = client.post("/api/v1/extract-cv?include=xyz", json={"cv_text": CV_TEXT})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "include chỉ nhận kg, raw"

    resp_mixed = client.post("/api/v1/extract-cv?include=kg,invalid", json={"cv_text": CV_TEXT})
    assert resp_mixed.status_code == 400
    assert resp_mixed.json()["detail"] == "include chỉ nhận kg, raw"


def test_soft_skills_stay_verbatim_and_tech_is_renamed():
    """Soft skills keep the CV wording; technical skills take the KB canonical name (real seed)."""
    from pathlib import Path

    from app.kb.normalize import normalize_profile_with_kb
    from app.kb.store import KnowledgeBase

    kb = KnowledgeBase.from_csv(Path(__file__).resolve().parents[1] / "kb" / "seed")
    out = normalize_profile_with_kb({"skills": ["Làm việc nhóm", "teamwork", "ReactJS", "PyTorch"]}, kb)
    assert out["skills"] == ["Làm việc nhóm", "teamwork", "React", "PyTorch"]
