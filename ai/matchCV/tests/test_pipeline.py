import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.features import extract_features
from app.main import app
from app.normalize import normalize_candidate, normalize_jd
from app.scoring import compute_final_score


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def hash_embeddings(monkeypatch):
    monkeypatch.setenv("MATCHMAKING_EMBEDDING_BACKEND", "hash")


def test_five_fixture_pairs_have_valid_scores():
    for path in sorted(FIXTURES.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        candidate = normalize_candidate(payload["candidate"])
        jd = normalize_jd(payload["jd"])
        features, _, _ = extract_features(candidate, jd)
        assert all(0 <= value <= 1 for value in features.values())
        assert 0 <= compute_final_score(features) <= 100


def test_normalization_handles_missing_fields():
    assert normalize_candidate({})["skills"] == []
    assert normalize_jd({})["required_skills"] == []


def test_match_endpoint_returns_contract():
    client = TestClient(app)
    response = client.post("/match", json={"candidate": {"skills": ["ReactJS"]}, "jd": {"required_skills": ["React"]}})
    assert response.status_code == 200
    assert {"score", "missing_skills", "matched_skills", "feature_scores", "reasoning"} <= response.json().keys()


def test_legacy_schema_and_no_llm_endpoint():
    client = TestClient(app)
    response = client.post(
        "/match/no-llm",
        json={
            "candidate": {
                "skills": ["JS"],
                "education": {"degree": "Cử nhân", "major": "CNTT"},
                "certificates": ["AWS"],
            },
            "jd": {
                "required_skills": ["JavaScript"],
                "education_requirement": "Cử nhân CNTT trở lên",
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["matched_skills"] == ["javascript"]
    assert "processing_time_ms" in response.json()


def test_partial_weights_are_completed():
    client = TestClient(app)
    response = client.post(
        "/match/no-llm",
        json={
            "candidate": {"skills": ["Python"]},
            "jd": {"required_skills": ["Python"]},
            "weights": {"skill": 1.0},
        },
    )
    assert response.status_code == 200
    assert response.json()["weights_used"]["context"] == 0.15
