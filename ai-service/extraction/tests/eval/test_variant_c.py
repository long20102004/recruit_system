"""Unit tests for evaluation variant C, canonical skills metric, and KG reporting.

All tests use synthetic data only; no real CV or database connection is used.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.kb.store import KnowledgeBase
from app.postprocess.schema import normalize_profile
from eval.metrics import aggregate, score_sample
from eval.report import build_report
from eval.variants import VARIANTS, VARIANT_ORDER, get_kb


def _create_synthetic_kb(tmp_path: Path) -> KnowledgeBase:
    """Create a small in-memory KnowledgeBase using CSV files in tmp_path."""
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir(parents=True, exist_ok=True)

    skills_csv = seed_dir / "skills.csv"
    skills_csv.write_text(
        "id,name,category,reviewed\n"
        "1,ReactJS,Frontend,true\n"
        "2,JavaScript,Programming Language,true\n"
        "3,Java,Programming Language,true\n"
        "4,Spring Boot,Framework,true\n",
        encoding="utf-8",
    )

    aliases_csv = seed_dir / "skill_aliases.csv"
    aliases_csv.write_text(
        "alias_key,skill_id,surface\n"
        "reactjs,1,React.js\n"
        "reactjs,1,ReactJS\n"
        "javascript,2,JavaScript\n"
        "java,3,Java\n"
        "springboot,4,Spring Boot\n",
        encoding="utf-8",
    )

    edges_csv = seed_dir / "skill_edges.csv"
    edges_csv.write_text(
        "src_id,rel,dst_id\n"
        "4,REQUIRES,3\n",
        encoding="utf-8",
    )

    unis_csv = seed_dir / "universities.csv"
    unis_csv.write_text(
        "id,name\n"
        "100,Học viện Công nghệ Bưu chính Viễn thông\n",
        encoding="utf-8",
    )

    uni_alias_csv = seed_dir / "university_aliases.csv"
    uni_alias_csv.write_text(
        "alias_key,university_id\n"
        "ptit,100\n",
        encoding="utf-8",
    )

    return KnowledgeBase.from_csv(seed_dir)


def test_variant_order_contains_c():
    """Verify VARIANT_ORDER contains ('A', 'B', 'C') and C is in VARIANTS."""
    assert VARIANT_ORDER == ("A", "B", "C")
    assert "C" in VARIANTS


def test_variant_c_enriches_skills_and_implies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Variant C adds skills_normalized and implied_skills without mutating raw skills."""
    kb = _create_synthetic_kb(tmp_path)
    monkeypatch.setattr("eval.variants.get_kb", lambda: kb)

    cv_text = "Kinh nghiệm: Phát triển dự án bằng Spring Boot."
    raw_pred = {
        "personal_info": {"full_name": "Nguyen Van A"},
        "skills": ["Spring Boot"],
        "education": [],
        "experience": [],
    }

    fn_c = VARIANTS["C"]
    enriched = fn_c(raw_pred, cv_text)

    assert isinstance(enriched, dict)
    assert "skills_normalized" in enriched
    assert len(enriched["skills_normalized"]) == 1
    norm_skill = enriched["skills_normalized"][0]
    assert norm_skill["id"] == 4
    assert norm_skill["name"] == "Spring Boot"

    assert "implied_skills" in enriched
    assert len(enriched["implied_skills"]) == 1
    implied = enriched["implied_skills"][0]
    assert implied["id"] == 3
    assert implied["name"] == "Java"
    assert implied["via"] == [{"from": "Spring Boot", "rel": "REQUIRES"}]

    # Original skills remain unchanged
    assert enriched["skills"] == ["Spring Boot"]


def test_skills_canonical_maps_synonyms_to_same_id(tmp_path: Path):
    """skills_canonical considers 'React.js' and 'ReactJS' as same ID -> TP; string F1 differs."""
    kb = _create_synthetic_kb(tmp_path)
    cv_text = "Kỹ năng chuyên môn: React.js"

    # Pred has 'React.js', Gold has 'ReactJS'
    pred = {"skills": ["React.js"]}
    gold = {"skills": ["ReactJS"]}

    # Without linker: exact normalized string comparison gives TP=0, FP=1, FN=1
    s_string = score_sample(pred, gold, cv_text, linker=None)
    assert s_string["skills"]["tp"] == 0
    assert s_string["skills"]["fp"] == 1
    assert s_string["skills"]["fn"] == 1
    assert "skills_canonical" not in s_string

    # With linker: both map to id:1 -> TP=1, FP=0, FN=0
    s_canon = score_sample(pred, gold, cv_text, linker=kb.linker)
    assert "skills_canonical" in s_canon
    assert s_canon["skills_canonical"]["tp"] == 1
    assert s_canon["skills_canonical"]["fp"] == 0
    assert s_canon["skills_canonical"]["fn"] == 0


def test_aggregate_includes_kg_metrics():
    """Aggregate metrics include kg.implied_per_cv, unlinked_rate, and skills_canonical F1."""
    from app.postprocess.schema import normalize_profile

    empty = normalize_profile(None)
    base = score_sample(empty, empty, "")  # complete score dict; then override KG parts
    s1 = {
        **base,
        "valid": True,
        "kg": {"implied": 1, "unlinked": 0, "linked": 1},
        "skills_canonical": {"tp": 1, "fp": 0, "fn": 0},
    }
    s2 = {
        **base,
        "valid": True,
        "kg": {"implied": 0, "unlinked": 1, "linked": 0},
        "skills_canonical": {"tp": 0, "fp": 1, "fn": 1},
    }

    agg = aggregate([s1, s2])
    assert "kg" in agg
    assert pytest.approx(agg["kg"]["implied_per_cv"]) == 0.5
    assert pytest.approx(agg["kg"]["unlinked_rate"]) == 0.5
    assert "skills_canonical" in agg
    assert pytest.approx(agg["skills_canonical"]["f1"]) == 0.5


def test_build_report_generates_table_with_variant_c(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """build_report runs with 2 synthetic samples + predictions.jsonl and outputs column C."""
    kb = _create_synthetic_kb(tmp_path)
    monkeypatch.setattr("eval.variants.get_kb", lambda: kb)

    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    cv_1 = "CV 1 with React.js skills and experience"
    cv_2 = "CV 2 with Spring Boot backend framework"

    s1_id = hashlib.sha1(cv_1.encode("utf-8")).hexdigest()[:12]
    s2_id = hashlib.sha1(cv_2.encode("utf-8")).hexdigest()[:12]

    sample1_gold = normalize_profile({"skills": ["ReactJS"]})
    sample2_gold = normalize_profile({"skills": ["Java"]})

    split_file = tmp_path / "val_synth.jsonl"
    split_file.write_text(
        json.dumps({"input": cv_1, "output": sample1_gold}) + "\n"
        + json.dumps({"input": cv_2, "output": sample2_gold}) + "\n",
        encoding="utf-8",
    )

    pred_file = run_dir / "predictions.jsonl"
    pred_file.write_text(
        json.dumps({
            "id": s1_id,
            "status": 200,
            "data": {"skills": ["React.js"]},
            "latency_s": 0.15,
        }) + "\n"
        + json.dumps({
            "id": s2_id,
            "status": 200,
            "data": {"skills": ["Spring Boot"]},
            "latency_s": 0.25,
        }) + "\n",
        encoding="utf-8",
    )

    report_data = build_report(
        run_dir=run_dir,
        split_paths=[split_file],
        variants=("A", "B", "C"),
    )

    assert "splits" in report_data
    split_res = report_data["splits"]["val_synth"]
    assert "A" in split_res
    assert "B" in split_res
    assert "C" in split_res

    # Variant C contains kg_ms_per_cv metric
    c_metrics = split_res["C"]["metrics"]
    assert "kg_ms_per_cv" in c_metrics
    assert isinstance(c_metrics["kg_ms_per_cv"], (int, float))

    md_content = (run_dir / "report.md").read_text(encoding="utf-8")

    # Table contains column C
    assert "val_synth / C" in md_content

    # Table contains required new rows
    assert "skills_canonical (F1)" in md_content
    assert "implied skills / CV" in md_content
    assert "unlinked skill rate" in md_content
    assert "KG ms / CV" in md_content
