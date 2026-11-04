"""Unit tests for kb.build_seed (synthetic data only)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from kb.build_seed import CATEGORIES, build_seed, main
from kb.load import read_seed, validate


def _create_synthetic_train_jsonl(path: Path, records: list[dict]) -> None:
    lines = [json.dumps({"input": f"CV text {i}", "output": rec}) for i, rec in enumerate(records)]
    path.write_text("\n".join(lines), encoding="utf-8")


def _create_dummy_java_file(path: Path) -> None:
    code = """package recruit.demo.extraction.section;

public final class SectionDictionary {
    static {
        reg(CvSection.OBJECTIVE,
                "MỤC TIÊU", "OBJECTIVE", "TÓM TẮT");
        reg(CvSection.EDUCATION,
                "HỌC VẤN", "EDUCATION", "GIÁO DỤC");
        reg(CvSection.EXPERIENCE,
                "KINH NGHIỆM LÀM VIỆC", "EXPERIENCE", "MỤC TIÊU"); // Duplicate heading test
    }
}
"""
    path.write_text(code, encoding="utf-8")


@pytest.fixture
def base_setup(tmp_path: Path):
    train_file = tmp_path / "train.jsonl"
    curated_dir = tmp_path / "curated"
    out_dir = tmp_path / "seed"
    java_file = tmp_path / "SectionDictionary.java"

    curated_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    _create_dummy_java_file(java_file)

    # 4 synthetic CVs
    records = [
        {
            "skills": ["React", "ReactJS", "Java", "Spring Boot", "Java & Spring Boot"],
            "education": [{"school": "Trường Đại học Bách khoa Hà Nội"}],
            "experience": [{"job_title": "Backend Developer"}],
            "personal_projects": [{"tech_stack": ["React", "Docker"]}],
        },
        {
            "skills": ["React", "Python"],
            "education": [{"school": "HUST"}],
            "experience": [{"job_title": "backend developer"}],
            "personal_projects": [{"tech_stack": ["PostgreSQL"]}],
        },
        {
            "skills": ["React", "React.js", "Java"],
            "education": [{"school": "Đại học Quốc gia Hà Nội"}],
            "experience": [{"job_title": "Frontend Engineer"}],
            "personal_projects": [],
        },
        {
            "skills": ["Spring Boot"],
            "education": [{"school": "HUST"}],
            "experience": [{"job_title": "Backend Developer"}],
            "personal_projects": [],
        },
    ]
    _create_synthetic_train_jsonl(train_file, records)

    return {
        "train_file": train_file,
        "curated_dir": curated_dir,
        "out_dir": out_dir,
        "java_file": java_file,
    }


def test_build_seed_canonical_by_frequency(base_setup) -> None:
    """React (freq 4) / ReactJS (freq 1) / React.js (freq 1) -> canonical 'React'."""
    summary = build_seed(
        train_path=base_setup["train_file"],
        out_dir=base_setup["out_dir"],
        curated_dir=base_setup["curated_dir"],
        section_dict_path=base_setup["java_file"],
    )

    seed = read_seed(base_setup["out_dir"])
    react_skills = [s for s in seed["skills"] if s["name"] == "React"]
    assert len(react_skills) == 1
    assert react_skills[0]["name"] == "React"

    # Alias check
    react_alias = [a for a in seed["skill_aliases"] if a["alias_key"] == "react"]
    assert len(react_alias) == 1
    assert react_alias[0]["surface"] == "React"


def test_build_seed_composite_dropped_when_components_exist(base_setup) -> None:
    """'Java & Spring Boot' dropped when Java and Spring Boot exist."""
    summary = build_seed(
        train_path=base_setup["train_file"],
        out_dir=base_setup["out_dir"],
        curated_dir=base_setup["curated_dir"],
        section_dict_path=base_setup["java_file"],
    )

    assert summary["composites_dropped"] >= 1
    seed = read_seed(base_setup["out_dir"])
    skill_names = {s["name"] for s in seed["skills"]}
    assert "Java" in skill_names
    assert "Spring Boot" in skill_names
    assert "Java & Spring Boot" not in skill_names


def test_build_seed_composite_kept_with_curated(base_setup) -> None:
    """'Java & Spring Boot' is kept when keep_composite=true in curated."""
    cat_curated = base_setup["curated_dir"] / "skill_categories_curated.csv"
    with cat_curated.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["key", "category", "keep_composite", "reviewed"])
        writer.writerow(["javaspringboot", "Framework/Library", "true", "true"])

    summary = build_seed(
        train_path=base_setup["train_file"],
        out_dir=base_setup["out_dir"],
        curated_dir=base_setup["curated_dir"],
        section_dict_path=base_setup["java_file"],
    )

    assert summary["composites_dropped"] == 0
    seed = read_seed(base_setup["out_dir"])
    skill_names = {s["name"] for s in seed["skills"]}
    assert "Java & Spring Boot" in skill_names
    javasb = next(s for s in seed["skills"] if s["name"] == "Java & Spring Boot")
    assert javasb["category"] == "Framework/Library"
    assert javasb["reviewed"] == "true"


def test_build_seed_categories_applied_and_defaults(base_setup) -> None:
    """Category curated applied (reviewed=true); missing -> Other (reviewed=false)."""
    cat_curated = base_setup["curated_dir"] / "skill_categories_curated.csv"
    with cat_curated.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["key", "category", "keep_composite", "reviewed"])
        writer.writerow(["react", "Frontend", "false", "true"])
        writer.writerow(["python", "Programming Language", "false", "true"])

    summary = build_seed(
        train_path=base_setup["train_file"],
        out_dir=base_setup["out_dir"],
        curated_dir=base_setup["curated_dir"],
        section_dict_path=base_setup["java_file"],
    )

    assert summary["skills_reviewed"] == 2
    seed = read_seed(base_setup["out_dir"])
    skills_by_name = {s["name"]: s for s in seed["skills"]}

    assert skills_by_name["React"]["category"] == "Frontend"
    assert skills_by_name["React"]["reviewed"] == "true"
    assert skills_by_name["Python"]["category"] == "Programming Language"
    assert skills_by_name["Python"]["reviewed"] == "true"

    # Java has no curated category -> Other, reviewed=false
    assert skills_by_name["Java"]["category"] == "Other"
    assert skills_by_name["Java"]["reviewed"] == "false"


def test_build_seed_invalid_category_raises(base_setup) -> None:
    """Invalid category in curated raises ValueError."""
    cat_curated = base_setup["curated_dir"] / "skill_categories_curated.csv"
    with cat_curated.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["key", "category", "keep_composite", "reviewed"])
        writer.writerow(["react", "NonExistentCategory", "false"])

    with pytest.raises(ValueError, match="Invalid category 'NonExistentCategory'"):
        build_seed(
            train_path=base_setup["train_file"],
            out_dir=base_setup["out_dir"],
            curated_dir=base_setup["curated_dir"],
            section_dict_path=base_setup["java_file"],
        )


def test_build_seed_edges_resolved_and_unresolved(base_setup) -> None:
    """Curated edge resolves to IDs; unresolved names collected without raising."""
    edge_curated = base_setup["curated_dir"] / "skill_edges_curated.csv"
    with edge_curated.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["src_name", "rel", "dst_name"])
        writer.writerow(["Spring Boot", "REQUIRES", "Java"])
        writer.writerow(["Spring Boot", "REQUIRES", "UnknownSkillXYZ"])

    summary = build_seed(
        train_path=base_setup["train_file"],
        out_dir=base_setup["out_dir"],
        curated_dir=base_setup["curated_dir"],
        section_dict_path=base_setup["java_file"],
    )

    assert summary["edges"] == 1
    assert "UnknownSkillXYZ" in summary["edges_unresolved"]

    seed = read_seed(base_setup["out_dir"])
    skills_by_name = {s["name"]: s["id"] for s in seed["skills"]}
    assert len(seed["skill_edges"]) == 1
    edge = seed["skill_edges"][0]
    assert edge["src_id"] == skills_by_name["Spring Boot"]
    assert edge["rel"] == "REQUIRES"
    assert edge["dst_id"] == skills_by_name["Java"]


def test_build_seed_universities_merged_curated(base_setup) -> None:
    """Gold schools merged into canonical university according to curated."""
    uni_curated = base_setup["curated_dir"] / "university_curated.csv"
    with uni_curated.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["key", "canonical_name", "extra_aliases", "reviewed"])
        writer.writerow(
            ["bach khoa ha noi", "Hanoi University of Science and Technology", "HUST|BK", "true"]
        )

    summary = build_seed(
        train_path=base_setup["train_file"],
        out_dir=base_setup["out_dir"],
        curated_dir=base_setup["curated_dir"],
        section_dict_path=base_setup["java_file"],
    )

    seed = read_seed(base_setup["out_dir"])
    unis_by_name = {u["name"]: u for u in seed["universities"]}
    assert "Hanoi University of Science and Technology" in unis_by_name
    hust = unis_by_name["Hanoi University of Science and Technology"]
    assert hust["reviewed"] == "true"

    # Both "bach khoa ha noi" and "hust" aliases point to HUST
    hust_aliases = [
        a for a in seed["university_aliases"] if a["university_id"] == hust["id"]
    ]
    alias_keys = {a["alias_key"] for a in hust_aliases}
    assert "bach khoa ha noi" in alias_keys
    assert "hust" in alias_keys
    assert "bk" in alias_keys


def test_build_seed_section_headings_dummy_java(base_setup) -> None:
    """Section headings parsed from Java file, unique, sorted."""
    summary = build_seed(
        train_path=base_setup["train_file"],
        out_dir=base_setup["out_dir"],
        curated_dir=base_setup["curated_dir"],
        section_dict_path=base_setup["java_file"],
    )

    seed = read_seed(base_setup["out_dir"])
    headings = {h["heading"]: h["section"] for h in seed["section_headings"]}
    assert headings["MỤC TIÊU"] == "OBJECTIVE"
    assert headings["OBJECTIVE"] == "OBJECTIVE"
    assert headings["EDUCATION"] == "EDUCATION"
    assert headings["EXPERIENCE"] == "EXPERIENCE"

    # Check deduplication: "MỤC TIÊU" was defined in both OBJECTIVE and EXPERIENCE
    # It must retain its first section (OBJECTIVE)
    matching = [h for h in seed["section_headings"] if h["heading"] == "MỤC TIÊU"]
    assert len(matching) == 1
    assert matching[0]["section"] == "OBJECTIVE"


def test_build_seed_output_clean_and_idempotent(base_setup, tmp_path: Path) -> None:
    """Validate returns 0 errors; running twice yields identical byte output."""
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"

    summary1 = build_seed(
        train_path=base_setup["train_file"],
        out_dir=out1,
        curated_dir=base_setup["curated_dir"],
        section_dict_path=base_setup["java_file"],
    )
    summary2 = build_seed(
        train_path=base_setup["train_file"],
        out_dir=out2,
        curated_dir=base_setup["curated_dir"],
        section_dict_path=base_setup["java_file"],
    )

    assert summary1 == summary2

    # Validation check
    seed1 = read_seed(out1)
    errors = validate(seed1)
    assert errors == []

    # File-by-file byte-identical check
    files = [
        "categories.csv",
        "skills.csv",
        "skill_aliases.csv",
        "skill_edges.csv",
        "universities.csv",
        "university_aliases.csv",
        "job_titles.csv",
        "section_headings.csv",
    ]
    for fn in files:
        content1 = (out1 / fn).read_bytes()
        content2 = (out2 / fn).read_bytes()
        assert content1 == content2, f"Mismatch in {fn}"


def test_build_seed_job_titles_extraction(base_setup) -> None:
    """Job titles extracted from experience, canonical chosen by frequency."""
    summary = build_seed(
        train_path=base_setup["train_file"],
        out_dir=base_setup["out_dir"],
        curated_dir=base_setup["curated_dir"],
        section_dict_path=base_setup["java_file"],
    )

    seed = read_seed(base_setup["out_dir"])
    jt_names = {jt["name"]: jt["alias_key"] for jt in seed["job_titles"]}
    # 'Backend Developer' appeared 2 times, 'backend developer' 1 time -> 'Backend Developer'
    assert "Backend Developer" in jt_names
    assert "Frontend Engineer" in jt_names
    assert jt_names["Backend Developer"] == "backend developer"


def test_build_seed_cli(base_setup, capsys) -> None:
    """CLI prints valid JSON summary with correct keys."""
    test_args = [
        "kb.build_seed",
        "--train",
        str(base_setup["train_file"]),
        "--out",
        str(base_setup["out_dir"]),
        "--curated",
        str(base_setup["curated_dir"]),
        "--section-dict",
        str(base_setup["java_file"]),
    ]
    with patch("sys.argv", test_args):
        main()

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    expected_keys = {
        "skills",
        "aliases",
        "composites_dropped",
        "skills_reviewed",
        "edges",
        "edges_unresolved",
        "universities",
        "job_titles",
        "section_headings",
    }
    assert expected_keys.issubset(summary.keys())
    assert summary["skills"] > 0


def test_build_seed_llm_proposal_not_marked_reviewed(base_setup):
    """Curated rows without reviewed=true (e.g. LLM proposals) keep reviewed=false."""
    cat_curated = base_setup["curated_dir"] / "skill_categories_curated.csv"
    with cat_curated.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["key", "category", "keep_composite", "reviewed"])
        writer.writerow(["react", "Frontend", "false", "false"])
    build_seed(
        train_path=base_setup["train_file"],
        out_dir=base_setup["out_dir"],
        curated_dir=base_setup["curated_dir"],
        section_dict_path=base_setup["java_file"],
    )
    with (base_setup["out_dir"] / "skills.csv").open(encoding="utf-8") as f:
        rows = {r["name"]: r for r in csv.DictReader(f)}
    assert rows["React"]["category"] == "Frontend"
    assert rows["React"]["reviewed"] == "false"


def test_fuzzy_merge_folds_rare_typos_into_frequent_key():
    from kb.build_seed import _fuzzy_merge_targets

    groups = {
        "postgresql": {"PostgreSQL": 5},
        "postgreql": {"PostgreQl": 1},
        "restapi": {"REST API": 9},
        "restapis": {"REST APIs": 2},
        "gitlabci": {"GitLab CI": 3},
        "gitlabcicd": {"GitLab CI/CD": 4},
        "java": {"Java": 10},
        "javafx": {"JavaFX": 1},
    }
    merged = _fuzzy_merge_targets(groups, set(groups), {})
    assert merged["postgreql"] == "postgresql"
    assert merged["restapis"] == "restapi"
    assert "gitlabci" not in merged  # 89 < 90: distinct products stay separate
    assert "javafx" not in merged  # short/different skill not folded


def test_reference_universities_drop_ambiguous_aliases(tmp_path):
    from kb.build_seed import _read_reference_universities
    from app.kb.keys import school_key

    p = tmp_path / "vn_universities.csv"
    p.write_text(
        "name_vi,name_en,abbreviation,group\n"
        "Học viện Công nghệ Bưu chính Viễn thông,Posts & Telecoms Institute of Technology,PTIT,\n"
        "Đại học Duy Tân,,DTU,\n"
        "Trường Đại học Đồng Tháp,Dong Thap University,DTU,\n"
        "\"Trường Đại học Kinh tế, Đại học Huế\",Hue University College of Economics,HCE,Đại học Huế\n"
        "\"Trường Đại học Kinh tế, Đại học Đà Nẵng\",Danang University of Economics,DUE,Đại học Đà Nẵng\n",
        encoding="utf-8",
    )
    unis, alias = _read_reference_universities(p)
    assert alias[school_key("PTIT")] == "Học viện Công nghệ Bưu chính Viễn thông"
    assert school_key("DTU") not in alias  # shared abbreviation -> ambiguous
    assert school_key("Trường Đại học Kinh tế") not in alias  # member name without parent
    assert alias[school_key("DUE")] == "Trường Đại học Kinh tế, Đại học Đà Nẵng"
    assert len(unis) == 5
