"""Unit tests for silver dataset cleaner (US1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kb.clean_silver import clean_file, clean_record, is_infected, main


def test_infected_regex_matching():
    """Verify regex correctly distinguishes infected group labels from normal items."""
    # Infected group labels
    assert is_infected("Backend: Spring Boot, Node.js")
    assert is_infected("Tools: Docker, Git")
    assert is_infected("Database: PostgreSQL")
    assert is_infected("  Languages: Python, Go")

    # Not infected
    assert not is_infected("Spring Boot (Web, Data JPA)")
    assert not is_infected("ReactJS")
    assert not is_infected("Node.js")
    assert not is_infected("Java")
    assert not is_infected("Backend:")  # No non-whitespace after colon
    assert not is_infected("Backend:   ")
    assert not is_infected("")
    assert not is_infected(123)
    assert not is_infected(None)


def test_clean_record_group_label_skills_at_exact_position():
    """'Backend: Spring Boot, Node.js' -> ['Spring Boot', 'Node.js'] at the exact same position."""
    rec = {
        "file": "test1.pdf",
        "instruction": "extract",
        "input": "Sample CV text",
        "output": json.dumps(
            {
                "skills": ["Java", "Backend: Spring Boot, Node.js", "Docker"],
                "education": [{"school": "PTIT"}],
            },
            ensure_ascii=False,
        ),
    }

    cleaned_rec, stats = clean_record(rec)

    assert stats["changed"] is True
    assert stats["items_stripped"] == 1
    assert stats["items_added"] == 1  # 2 produced - 1 stripped = +1

    parsed_output = json.loads(cleaned_rec["output"])
    # Position check: Java (0), Spring Boot (1), Node.js (2), Docker (3)
    assert parsed_output["skills"] == ["Java", "Spring Boot", "Node.js", "Docker"]
    # Unrelated fields preserved
    assert parsed_output["education"] == [{"school": "PTIT"}]
    assert cleaned_rec["file"] == "test1.pdf"
    assert cleaned_rec["input"] == "Sample CV text"


def test_clean_record_uninfected_returns_same_object():
    """Uninfected record returns identical object without changes."""
    rec = {
        "file": "test2.pdf",
        "input": "Sample CV text",
        "output": json.dumps(
            {
                "skills": ["Spring Boot (Web, Data JPA)", "ReactJS", "Docker"],
            },
            ensure_ascii=False,
        ),
    }

    cleaned_rec, stats = clean_record(rec)

    assert stats == {"changed": False, "items_stripped": 0, "items_added": 0}
    # Must be the exact same object to allow byte-identical write
    assert cleaned_rec is rec


def test_spring_boot_parentheses_not_infected():
    """'Spring Boot (Web, Data JPA)' is not treated as infected and is kept intact."""
    skills = ["Python", "Spring Boot (Web, Data JPA)", "Git"]
    rec = {
        "output": {
            "skills": skills,
        }
    }

    cleaned_rec, stats = clean_record(rec)

    assert stats["changed"] is False
    assert cleaned_rec is rec
    assert cleaned_rec["output"]["skills"] == ["Python", "Spring Boot (Web, Data JPA)", "Git"]


def test_clean_record_tech_stack_in_personal_projects():
    """Infected items in personal_projects.tech_stack are also cleaned."""
    rec = {
        "output": json.dumps(
            {
                "skills": ["Java"],
                "personal_projects": [
                    {
                        "name": "E-Commerce",
                        "tech_stack": ["Backend: Spring Boot, PostgreSQL", "Docker"],
                    },
                    {
                        "name": "Portfolio",
                        "tech_stack": ["Frontend: React, Tailwind CSS"],
                    },
                ],
            },
            ensure_ascii=False,
        )
    }

    cleaned_rec, stats = clean_record(rec)

    assert stats["changed"] is True
    assert stats["items_stripped"] == 2
    assert stats["items_added"] == 2  # (2-1) + (2-1) = 2

    parsed_output = json.loads(cleaned_rec["output"])
    assert parsed_output["skills"] == ["Java"]
    assert parsed_output["personal_projects"][0]["tech_stack"] == [
        "Spring Boot",
        "PostgreSQL",
        "Docker",
    ]
    assert parsed_output["personal_projects"][1]["tech_stack"] == [
        "React",
        "Tailwind CSS",
    ]


def test_output_type_preservation():
    """Output string remains string; output dict remains dict."""
    # String output
    rec_str = {
        "output": json.dumps({"skills": ["Backend: Python, Django"]}),
    }
    cleaned_str, stats_str = clean_record(rec_str)
    assert stats_str["changed"] is True
    assert isinstance(cleaned_str["output"], str)
    assert json.loads(cleaned_str["output"])["skills"] == ["Python", "Django"]

    # Dict output
    rec_dict = {
        "output": {"skills": ["Backend: Python, Django"]},
    }
    cleaned_dict, stats_dict = clean_record(rec_dict)
    assert stats_dict["changed"] is True
    assert isinstance(cleaned_dict["output"], dict)
    assert cleaned_dict["output"]["skills"] == ["Python", "Django"]
    # Ensure original rec_dict was not mutated
    assert rec_dict["output"]["skills"] == ["Backend: Python, Django"]


def test_clean_file_summary_and_byte_identity(tmp_path: Path):
    """Verify clean_file counts, summaries, and byte-identical lines for unchanged records."""
    in_file = tmp_path / "in.jsonl"
    out_file = tmp_path / "out.jsonl"

    rec1 = {
        "input": "CV 1",
        "output": json.dumps({"skills": ["Java", "Docker"]}),
    }
    rec2 = {
        "input": "CV 2",
        "output": json.dumps({"skills": ["Java", "Backend: Spring Boot, Node.js"]}),
    }
    rec3 = {
        "input": "CV 3",
        "output": json.dumps(
            {
                "skills": ["Tools: Git"],  # 1 stripped, 1 produced -> added = 0
                "personal_projects": [
                    {"tech_stack": ["Database: MySQL, Redis"]}  # 1 stripped, 2 produced -> added = 1
                ],
            }
        ),
    }

    line1 = json.dumps(rec1, ensure_ascii=False) + "\n"
    line2 = json.dumps(rec2, ensure_ascii=False) + "\n"
    line3 = json.dumps(rec3, ensure_ascii=False) + "\n"
    empty_line = "\n"

    in_file.write_text(line1 + line2 + empty_line + line3, encoding="utf-8")

    summary = clean_file(in_file, out_file)

    assert summary["records"] == 3
    assert summary["records_changed"] == 2
    assert summary["items_stripped"] == 3  # 1 from rec2, 2 from rec3
    assert summary["items_added"] == 2  # (2-1) from rec2 + (1-1) + (2-1) from rec3 = 2

    # Verify line1 is byte-identical
    out_lines = out_file.read_text(encoding="utf-8").splitlines(keepends=True)
    assert out_lines[0] == line1
    # Verify empty line preserved
    assert out_lines[2] == "\n"

    # Verify rec2 parsed
    out_rec2 = json.loads(out_lines[1])
    assert json.loads(out_rec2["output"])["skills"] == ["Java", "Spring Boot", "Node.js"]


def test_clean_file_idempotency(tmp_path: Path):
    """Running clean_file on an already cleaned file yields 0 changes and identical bytes."""
    in_file = tmp_path / "dirty.jsonl"
    clean1 = tmp_path / "clean1.jsonl"
    clean2 = tmp_path / "clean2.jsonl"

    rec = {
        "input": "CV text",
        "output": json.dumps({"skills": ["Backend: Go, Rust", "Docker"]}),
    }
    in_file.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")

    # Run 1
    summary1 = clean_file(in_file, clean1)
    assert summary1["records_changed"] == 1
    assert summary1["items_stripped"] == 1
    assert summary1["items_added"] == 1

    # Run 2 on cleaned output
    summary2 = clean_file(clean1, clean2)
    assert summary2["records"] == 1
    assert summary2["records_changed"] == 0
    assert summary2["items_stripped"] == 0
    assert summary2["items_added"] == 0

    assert clean1.read_bytes() == clean2.read_bytes()


def test_cli_main(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Test CLI main() with multiple input files and --out-dir."""
    in_dir = tmp_path / "inputs"
    in_dir.mkdir()
    out_dir = tmp_path / "outputs"

    f1 = in_dir / "train.jsonl"
    f2 = in_dir / "val.jsonl"

    rec_train = {
        "output": json.dumps({"skills": ["Backend: Java, Kotlin"]}),
    }
    rec_val = {
        "output": json.dumps({"skills": ["Python"]}),
    }

    f1.write_text(json.dumps(rec_train) + "\n", encoding="utf-8")
    f2.write_text(json.dumps(rec_val) + "\n", encoding="utf-8")

    exit_code = main(["--in", str(f1), str(f2), "--out-dir", str(out_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert "files" in report
    assert "total" in report
    assert report["total"]["records"] == 2
    assert report["total"]["records_changed"] == 1
    assert report["total"]["items_stripped"] == 1
    assert report["total"]["items_added"] == 1

    assert (out_dir / "train.jsonl").exists()
    assert (out_dir / "val.jsonl").exists()


def test_malformed_and_edge_records():
    """Verify handling of empty or non-dict/unparseable outputs."""
    # Non-dict record
    assert clean_record("not a dict") == ("not a dict", {"changed": False, "items_stripped": 0, "items_added": 0})

    # Unparseable output string
    rec_bad_json = {"output": "{malformed json"}
    assert clean_record(rec_bad_json) == (rec_bad_json, {"changed": False, "items_stripped": 0, "items_added": 0})

    # Missing output or non-dict output
    rec_no_output = {"input": "something"}
    assert clean_record(rec_no_output) == (rec_no_output, {"changed": False, "items_stripped": 0, "items_added": 0})

    rec_int_output = {"output": 12345}
    assert clean_record(rec_int_output) == (rec_int_output, {"changed": False, "items_stripped": 0, "items_added": 0})
