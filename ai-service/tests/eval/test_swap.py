"""Unit tests for eval.swap (entity-swapped evaluation split builder).

Tests use synthetic data only; no real CV data is read or written.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.postprocess.schema import normalize_profile
from app.postprocess.text_match import normalize
from eval.swap import Sample, build_swap, main


def _make_sample(
    sample_id: str,
    cv_text: str,
    gold_profile: dict,
    instruction: str = "Trích xuất thông tin CV",
) -> Sample:
    normalized_gold = normalize_profile(gold_profile)
    raw = {
        "instruction": instruction,
        "input": cv_text,
        "output": json.dumps(normalized_gold, ensure_ascii=False),
    }
    return Sample(id=sample_id, cv_text=cv_text, gold=normalized_gold, raw=raw)


def test_swap_both_cv_and_gold() -> None:
    """Verifies that company and school names are replaced in both CV text and gold."""
    cv_text = (
        "Kinh nghiệm làm việc:\n"
        "- Công ty TNHH Phần mềm Mặt Trời (2020 - 2022): Backend Engineer\n"
        "Học vấn:\n"
        "- Trường Đại học Công nghệ Thông tin (2016 - 2020): Kỹ sư CNTT"
    )
    gold = {
        "experience": [{"company": "Công ty TNHH Phần mềm Mặt Trời", "job_title": "Backend Engineer"}],
        "education": [{"school": "Trường Đại học Công nghệ Thông tin", "major": "Kỹ sư CNTT"}],
    }
    sample = _make_sample("s1", cv_text, gold)

    rows, summary = build_swap([sample], train_samples=[], seed=42)

    assert summary["samples"] == 1
    assert summary["names_replaced"] == 2
    assert summary["occurrences_replaced"] == 2
    assert summary["names_not_found"] == 0
    assert summary["per_type"]["company"]["names_replaced"] == 1
    assert summary["per_type"]["school"]["names_replaced"] == 1

    row = rows[0]
    new_cv = row["input"]
    new_gold = json.loads(row["output"])

    # Original names must no longer exist
    assert "Phần mềm Mặt Trời" not in new_cv
    assert "Công nghệ Thông tin" not in new_cv
    assert new_gold["experience"][0]["company"] != "Công ty TNHH Phần mềm Mặt Trời"
    assert new_gold["education"][0]["school"] != "Trường Đại học Công nghệ Thông tin"

    # Replacement in gold matches replacement in CV text
    new_company = new_gold["experience"][0]["company"]
    new_school = new_gold["education"][0]["school"]
    assert new_company in new_cv
    assert new_school in new_cv


def test_swap_diacritics_matching() -> None:
    """Accented and unaccented variations still match and get replaced."""
    cv_text = "Lam viec tai cong ty co phan hoa sen tu nam 2021."
    gold = {
        "experience": [{"company": "Công ty Cổ phần Hoa Sen", "job_title": "Developer"}],
    }
    sample = _make_sample("s_diacritics", cv_text, gold)

    rows, summary = build_swap([sample], train_samples=[], seed=42)

    assert summary["names_replaced"] == 1
    assert summary["occurrences_replaced"] == 1
    assert summary["names_not_found"] == 0

    new_cv = rows[0]["input"]
    new_gold = json.loads(rows[0]["output"])

    assert "cong ty co phan hoa sen" not in new_cv.lower()
    new_company = new_gold["experience"][0]["company"]
    assert new_company in new_cv


def test_swap_no_midword_matching() -> None:
    """Substring matching inside a larger word is rejected (word boundary check)."""
    # 'ABCD' contains 'ABC', but 'ABC' should NOT match inside 'ABCD'
    cv_text = "Làm việc tại tập đoàn ABCD Corporation từ 2020."
    gold = {
        "experience": [{"company": "ABCD", "job_title": "Developer"}],
    }
    # Test with target that is substring of another word in CV
    sample_sub = _make_sample("s_sub", cv_text, {"experience": [{"company": "Corp", "job_title": "Dev"}]})
    # 'Corp' is followed by 'oration', so not at boundary
    rows, summary = build_swap([sample_sub], train_samples=[], seed=42)

    assert summary["names_not_found"] == 1
    assert summary["names_replaced"] == 0
    assert summary["occurrences_replaced"] == 0
    # Text and gold are preserved
    assert rows[0]["input"] == cv_text
    new_gold = json.loads(rows[0]["output"])
    assert new_gold["experience"][0]["company"] == "Corp"


def test_name_not_in_cv_kept_and_counted() -> None:
    """When a gold name is not present in the CV text, it is kept unchanged and counted."""
    cv_text = "Lập trình viên Python với 3 năm kinh nghiệm."
    gold = {
        "experience": [{"company": "Công ty Cổ phần Misa", "job_title": "Developer"}],
    }
    sample = _make_sample("s_not_found", cv_text, gold)

    rows, summary = build_swap([sample], train_samples=[], seed=42)

    assert summary["names_not_found"] == 1
    assert summary["names_replaced"] == 0
    assert summary["occurrences_replaced"] == 0
    assert rows[0]["input"] == cv_text
    new_gold = json.loads(rows[0]["output"])
    assert new_gold["experience"][0]["company"] == "Công ty Cổ phần Misa"


def test_seed_reproducibility() -> None:
    """Same seed produces identical swaps; different seed produces different names."""
    cv_text = (
        "Công ty Cổ phần Giải pháp Số A\n"
        "Trường Đại học Bách Khoa"
    )
    gold = {
        "experience": [{"company": "Công ty Cổ phần Giải pháp Số A"}],
        "education": [{"school": "Trường Đại học Bách Khoa"}],
    }
    sample = _make_sample("s_seed", cv_text, gold)

    rows_1, sum_1 = build_swap([sample], train_samples=[], seed=123)
    rows_2, sum_2 = build_swap([sample], train_samples=[], seed=123)
    rows_3, sum_3 = build_swap([sample], train_samples=[], seed=999)

    assert rows_1 == rows_2
    assert sum_1 == sum_2
    assert rows_1[0]["input"] != rows_3[0]["input"]


def test_fictitious_names_not_in_train() -> None:
    """Generated fictitious names do not overlap with training set entity names."""
    train_gold = {
        "experience": [
            {"company": "Công ty Cổ phần Viettel"},
            {"company": "Công ty TNHH Vanhloc Thuyphong Tech"},
        ],
        "education": [
            {"school": "Trường Đại học Quốc gia Hà Nội"},
            {"school": "Trường Đại học Vanhloc Khaiminh"},
        ],
    }
    train_sample = _make_sample("tr1", "CV train text", train_gold)

    val_cv = (
        "Công tác tại Công ty Cổ phần Viettel.\n"
        "Tốt nghiệp Trường Đại học Ngoại Thương."
    )
    val_gold = {
        "experience": [{"company": "Công ty Cổ phần Viettel"}],
        "education": [{"school": "Trường Đại học Ngoại Thương"}],
    }
    val_sample = _make_sample("val1", val_cv, val_gold)

    train_names = {
        normalize("Công ty Cổ phần Viettel"),
        normalize("Công ty TNHH Vanhloc Thuyphong Tech"),
        normalize("Trường Đại học Quốc gia Hà Nội"),
        normalize("Trường Đại học Vanhloc Khaiminh"),
    }

    rows, summary = build_swap([val_sample], train_samples=[train_sample], seed=42)
    new_gold = json.loads(rows[0]["output"])
    swapped_company = new_gold["experience"][0]["company"]
    swapped_school = new_gold["education"][0]["school"]

    assert normalize(swapped_company) not in train_names
    assert normalize(swapped_school) not in train_names


def test_short_names_skipped() -> None:
    """Normalized names shorter than 4 characters are skipped without counting as not found."""
    cv_text = "Thực tập tại FPT và học tại NEU."
    gold = {
        "experience": [{"company": "FPT", "job_title": "Intern"}],
        "education": [{"school": "NEU", "major": "MIS"}],
    }
    sample = _make_sample("s_short", cv_text, gold)

    rows, summary = build_swap([sample], train_samples=[], seed=42)

    assert summary["names_replaced"] == 0
    assert summary["occurrences_replaced"] == 0
    assert summary["names_not_found"] == 0
    assert rows[0]["input"] == cv_text


def test_same_orig_name_same_new_name_in_cv() -> None:
    """Same original entity name within a CV receives the exact same replacement name."""
    cv_text = (
        "2020: Lập trình viên tại Công ty Cổ phần VinaTech.\n"
        "2022: Kỹ sư trưởng tại Công ty Cổ phần VinaTech.\n"
        "Dự án được hỗ trợ bởi Công ty Cổ phần VinaTech."
    )
    gold = {
        "experience": [
            {"company": "Công ty Cổ phần VinaTech", "job_title": "Lập trình viên"},
            {"company": "Công ty Cổ phần VinaTech", "job_title": "Kỹ sư trưởng"},
        ],
    }
    sample = _make_sample("s_mult", cv_text, gold)

    rows, summary = build_swap([sample], train_samples=[], seed=42)

    assert summary["names_replaced"] == 1
    assert summary["occurrences_replaced"] == 3
    assert summary["names_not_found"] == 0

    new_gold = json.loads(rows[0]["output"])
    comp1 = new_gold["experience"][0]["company"]
    comp2 = new_gold["experience"][1]["company"]
    assert comp1 == comp2
    assert "VinaTech" not in rows[0]["input"]
    assert rows[0]["input"].count(comp1) == 3


def test_cli_execution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies CLI argument handling, file creation, and output JSON structure."""
    val_file = tmp_path / "val.jsonl"
    train_file = tmp_path / "train.jsonl"
    out_file = tmp_path / "val_swap.jsonl"

    train_data = {
        "instruction": "Test",
        "input": "Train CV",
        "output": json.dumps({"experience": [{"company": "Train Co"}]}),
    }
    val_data = {
        "instruction": "Test",
        "input": "Làm tại Công ty Alpha Tech.",
        "output": json.dumps({"experience": [{"company": "Công ty Alpha Tech"}]}),
    }

    train_file.write_text(json.dumps(train_data) + "\n", encoding="utf-8")
    val_file.write_text(json.dumps(val_data) + "\n", encoding="utf-8")

    test_args = [
        "swap.py",
        "--val", str(val_file),
        "--train", str(train_file),
        "--out", str(out_file),
        "--seed", "42",
    ]
    monkeypatch.setattr("sys.argv", test_args)

    main()

    assert out_file.exists()
    summary_file = tmp_path / "val_swap.summary.json"
    assert summary_file.exists()

    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary["samples"] == 1
    assert summary["names_replaced"] == 1
    assert summary["occurrences_replaced"] == 1
    assert summary["names_not_found"] == 0
