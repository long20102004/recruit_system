"""Unit tests for KB skill and school linking coverage measurement."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.kb.linker import Link, SkillLinker
from eval.dataset import Sample
from kb.measure import measure_schools, measure_skills, run


@pytest.fixture
def synthetic_seed_dir(tmp_path: Path) -> Path:
    seed_p = tmp_path / "seed"
    seed_p.mkdir(parents=True, exist_ok=True)

    # categories.csv
    with (seed_p / "categories.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "name"])
        w.writerow([1, "Framework/Library"])
        w.writerow([2, "Database"])
        w.writerow([3, "Programming Language"])

    # skills.csv
    with (seed_p / "skills.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "category", "reviewed"])
        w.writerow([1, "React", "Framework/Library", "true"])
        w.writerow([2, "Tailwind CSS", "Framework/Library", "true"])
        w.writerow([3, "PostgreSQL", "Database", "true"])
        w.writerow([4, "Java", "Programming Language", "true"])
        w.writerow([5, "Spring Boot", "Framework/Library", "true"])

    # skill_aliases.csv
    with (seed_p / "skill_aliases.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["alias_key", "skill_id", "surface"])
        w.writerow(["react", 1, "React"])
        w.writerow(["reactjs", 1, "ReactJS"])
        w.writerow(["tailwindcss", 2, "Tailwind CSS"])
        w.writerow(["postgresql", 3, "PostgreSQL"])
        w.writerow(["postgres", 3, "Postgres"])
        w.writerow(["java", 4, "Java"])
        w.writerow(["springboot", 5, "Spring Boot"])

    # universities.csv
    with (seed_p / "universities.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "reviewed"])
        w.writerow([1, "Đại học Bách khoa Hà Nội", "true"])
        w.writerow([2, "Học viện Bưu chính Viễn thông", "true"])

    # university_aliases.csv
    with (seed_p / "university_aliases.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["alias_key", "university_id", "surface"])
        w.writerow(["bach khoa ha noi", 1, "Đại học Bách khoa Hà Nội"])
        w.writerow(["buu chinh vien thong", 2, "Học viện Bưu chính Viễn thông"])

    return seed_p


@pytest.fixture
def synthetic_samples() -> list[Sample]:
    sample1 = Sample(
        id="s1",
        cv_text="CV 1 text",
        gold={
            "skills": [
                "react",         # exact
                "Tailwind-CSS",  # normalized
                "Postgress",     # fuzzy
            ],
            "education": [
                {"school": "Trường Đại học Bách khoa Hà Nội"},  # linked
            ],
        },
        raw={},
    )
    sample2 = Sample(
        id="s2",
        cv_text="CV 2 text",
        gold={
            "skills": [
                "Java & Spring Boot",           # split
                "Underwater Rocket Science",    # unlinked
            ],
            "education": [
                {"school": "Non-existent International University"},  # unlinked
            ],
        },
        raw={},
    )
    return [sample1, sample2]


def test_measure_skills(synthetic_seed_dir: Path, synthetic_samples: list[Sample]) -> None:
    linker = SkillLinker.from_csv(synthetic_seed_dir)
    res = measure_skills(synthetic_samples, linker)

    assert res["total"] == 5
    assert res["counts"]["exact"] == 1
    assert res["counts"]["normalized"] == 1
    assert res["counts"]["fuzzy"] == 1
    assert res["counts"]["split"] == 1
    assert res["counts"]["unlinked"] == 1

    # Top-level convenience getters
    assert res["exact"] == 1
    assert res["normalized"] == 1
    assert res["fuzzy"] == 1
    assert res["split"] == 1
    assert res["unlinked"] == 1

    # Shares
    assert res["shares"]["exact"] == pytest.approx(0.2)
    assert res["shares"]["normalized"] == pytest.approx(0.2)
    assert res["shares"]["fuzzy"] == pytest.approx(0.2)
    assert res["shares"]["split"] == pytest.approx(0.2)
    assert res["shares"]["unlinked"] == pytest.approx(0.2)

    assert res["linked_share"] == pytest.approx(0.8)
    assert res["distinct_skills_linked"] == 5
    assert res["unlinked_examples_count"] == 1


def test_measure_schools(synthetic_seed_dir: Path, synthetic_samples: list[Sample]) -> None:
    res = measure_schools(synthetic_samples, synthetic_seed_dir)

    assert res["total"] == 2
    assert res["linked"] == 1
    assert res["share"] == pytest.approx(0.5)


def test_run_report_generation(
    tmp_path: Path,
    synthetic_seed_dir: Path,
    synthetic_samples: list[Sample],
) -> None:
    split_file = tmp_path / "val.jsonl"
    with split_file.open("w", encoding="utf-8") as f:
        for s in synthetic_samples:
            row = {
                "input": s.cv_text,
                "output": s.gold,
            }
            f.write(json.dumps(row) + "\n")

    out_dir = tmp_path / "runs" / "kb"

    report = run(
        split_path=split_file,
        seed_dir=synthetic_seed_dir,
        out_dir=out_dir,
        dsn=None,
    )

    # Returned dict verification
    assert report["n_cv"] == 2
    assert "ms_per_cv" in report
    assert report["ms_per_cv"] >= 0.0
    assert report["skills"]["total"] == 5
    assert report["schools"]["total"] == 2
    assert "circularity caveat" in report["caveat"]

    # File artifacts verification
    json_path = out_dir / "linking_report.json"
    assert json_path.exists()
    loaded_json = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded_json["n_cv"] == 2
    assert loaded_json["skills"]["counts"]["exact"] == 1
    assert loaded_json["schools"]["linked"] == 1

    md_path = out_dir / "linking_report.md"
    assert md_path.exists()
    md_content = md_path.read_text(encoding="utf-8")
    assert "| Method | Count | Share |" in md_content
    assert "| exact |" in md_content
    assert "| normalized |" in md_content
    assert "| split |" in md_content
    assert "| fuzzy |" in md_content
    assert "| unlinked |" in md_content
    assert "KB seeded from train labels only; val never used for seeding; coverage on same-distribution data is optimistic (circularity caveat)" in md_content


def test_run_db_consistency_check(
    tmp_path: Path,
    synthetic_seed_dir: Path,
    synthetic_samples: list[Sample],
) -> None:
    split_file = tmp_path / "val.jsonl"
    with split_file.open("w", encoding="utf-8") as f:
        for s in synthetic_samples:
            row = {"input": s.cv_text, "output": s.gold}
            f.write(json.dumps(row) + "\n")

    out_dir = tmp_path / "runs" / "kb"

    csv_linker = SkillLinker.from_csv(synthetic_seed_dir)

    # Case 1: DB linker returns identical links -> consistent
    with patch.object(SkillLinker, "from_db", return_value=csv_linker):
        report = run(
            split_path=split_file,
            seed_dir=synthetic_seed_dir,
            out_dir=out_dir,
            dsn="postgresql://mock_dsn",
        )
        assert report["csv_db_consistent"] is True
        assert report["csv_db_mismatches"] == 0

    # Case 2: DB linker produces mismatch
    mock_mismatch_linker = MagicMock()
    mock_mismatch_linker.link.return_value = [
        Link(raw="mismatch", skill_id=999, name="Mismatch", category="Other", method="exact", score=100.0)
    ]
    with patch.object(SkillLinker, "from_db", return_value=mock_mismatch_linker):
        report_mismatch = run(
            split_path=split_file,
            seed_dir=synthetic_seed_dir,
            out_dir=out_dir,
            dsn="postgresql://mock_dsn",
        )
        assert report_mismatch["csv_db_consistent"] is False
        assert report_mismatch["csv_db_mismatches"] > 0


def test_measure_empty_samples(synthetic_seed_dir: Path) -> None:
    linker = SkillLinker.from_csv(synthetic_seed_dir)
    skill_res = measure_skills([], linker)
    assert skill_res["total"] == 0
    assert skill_res["linked_share"] == 0.0
    assert skill_res["distinct_skills_linked"] == 0
    assert skill_res["unlinked_examples_count"] == 0

    school_res = measure_schools([], synthetic_seed_dir)
    assert school_res["total"] == 0
    assert school_res["linked"] == 0
    assert school_res["share"] == 0.0
