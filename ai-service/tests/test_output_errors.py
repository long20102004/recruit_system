"""Feature 008: 502 on unusable model output, OUTPUT_TRUNCATED flag, skills_detected in the API (synthetic data)."""

import json
import logging

import pytest

from app.kb.store import KnowledgeBase, kb_state

CV = "SYNTHETIC CANDIDATE\nsyn.candidate@example.test\nSKILLS\nJava, Spring Boot, Docker"


@pytest.mark.parametrize("output", ["{}", '{"personal_info": {"full_name": null}, "skills": []}', "[1, 2]", "not json at all"])
def test_unusable_output_returns_502(client, fake_engine, caplog, output):
    fake_engine.output = output
    with caplog.at_level(logging.DEBUG):
        resp = client.post("/api/v1/extract-cv", json={"cv_text": CV})
    assert resp.status_code == 502
    assert "request_id=" in resp.json()["detail"]
    assert "syn.candidate@example.test" not in caplog.text


def test_loop_is_cut_and_flagged(client, fake_engine):
    bullet = "Built the same synthetic reporting feature again"
    fake_engine.output = json.dumps({"personal_info": {"full_name": "SYNTHETIC CANDIDATE"},
                                     "experience": [{"company": "Synthetic Co", "description": [bullet] * 6}]})
    resp = client.post("/api/v1/extract-cv", json={"cv_text": CV + "\nSynthetic Co\n" + bullet})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert {"code": "OUTPUT_TRUNCATED", "count": None, "field": "repeated_value"} in data["flags"]
    assert data["personal_info"]["full_name"] == "SYNTHETIC CANDIDATE"


def test_skills_detected_from_cv_text(client, fake_engine, tmp_path):
    (tmp_path / "skills.csv").write_text("id,name,category\n1,Java,Programming Language\n2,Docker,DevOps\n", encoding="utf-8")
    (tmp_path / "skill_edges.csv").write_text("src_id,rel,dst_id\n", encoding="utf-8")
    (tmp_path / "universities.csv").write_text("id,name\n", encoding="utf-8")
    (tmp_path / "university_aliases.csv").write_text("university_id,alias_key\n", encoding="utf-8")
    kb_state["kb"] = KnowledgeBase.from_csv(tmp_path)
    fake_engine.output = json.dumps({"personal_info": {"full_name": "SYNTHETIC CANDIDATE"}, "skills": ["Java"]})
    resp = client.post("/api/v1/extract-cv", json={"cv_text": CV})
    assert resp.status_code == 200
    detected = {s["name"]: s["source"] for s in resp.json()["data"]["skills_detected"]}
    assert detected == {"Java": "both", "Docker": "text"}
    assert not any(f["code"] == "OUTPUT_TRUNCATED" for f in resp.json()["data"]["flags"])
