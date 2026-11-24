"""Unit tests for evaluation dataset loading and metrics computation."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from eval.dataset import Sample, load_split, load_split_with_stats
from eval.metrics import aggregate, score_sample


# ============================================================================
# Synthetic Test Data
# ============================================================================

CV_TEXT_1 = """NGUYỄN VĂN A
Email: nguyen.vana@example.test
SĐT: 0912345678
GitHub: github.com/nguyenvana
Mục tiêu: Trở thành kỹ sư AI giỏi.
Học vấn: Trường Đại học Bách Khoa Hà Nội
Kinh nghiệm: Công ty FPT Software - Backend Developer
Dự án: Hệ thống Quản lý Tuyển dụng
Kỹ năng: Python, PyTorch, Docker
Chứng chỉ: AWS Certified Developer
Giải thưởng: Giải nhất Olympic Tin học
Ngôn ngữ: Tiếng Anh
"""

GOLD_1 = {
    "personal_info": {
        "full_name": "Nguyễn Văn A",
        "email": "nguyen.vana@example.test",
        "phone": "0912345678",
        "github_url": "https://github.com/nguyenvana",
    },
    "objective": "Trở thành kỹ sư AI giỏi.",
    "education": [{"school": "Trường Đại học Bách Khoa Hà Nội"}],
    "experience": [{"company": "Công ty FPT Software", "job_title": "Backend Developer"}],
    "personal_projects": [{"name": "Hệ thống Quản lý Tuyển dụng"}],
    "skills": ["Python", "PyTorch", "Docker"],
    "certificates": ["AWS Certified Developer"],
    "honours": ["Giải nhất Olympic Tin học"],
    "languages": [{"language": "Tiếng Anh"}],
}

PRED_1 = {
    "personal_info": {
        "full_name": "Nguyen Van A",
        "email": "nguyen.vana@example.test",
        "phone": "0912345678",
        "github_url": "https://www.github.com/nguyenvana/",
    },
    "objective": "Tro thanh ky su AI gioi.",
    "education": [{"school": "Truong Dai hoc Bach Khoa Ha Noi"}],
    "experience": [{"company": "Cong ty FPT Software", "job_title": "backend developer"}],
    "personal_projects": [{"name": "He thong Quan ly Tuyen dung"}],
    "skills": ["python", "pytorch", "Docker"],
    "certificates": ["AWS Certified Developer"],
    "honours": ["Giai nhat Olympic Tin hoc"],
    "languages": [{"language": "tieng anh"}],
}

CV_TEXT_2 = """TRẦN THỊ B
Email: tranb@example.test
Điện thoại: +84 912 345 678
Kinh nghiệm làm việc:
Công ty VNG - Frontend Engineer
Kỹ năng: Java, SQL
"""

GOLD_2 = {
    "personal_info": {
        "full_name": "Trần Thị B",
        "email": "tranb@example.test",
        "phone": "+84 912 345 678",  # digits: '84912345678'
        "github_url": None,
    },
    "objective": None,
    "education": [{"school": "Đại học Công nghệ"}],  # Absent in CV & absent in pred -> FN for pred, ungrounded in gold
    "experience": [
        {"company": "Công ty VNG", "job_title": "Frontend Engineer"},
        {"company": "Viettel", "job_title": "Data Analyst"},  # Absent in CV & pred
    ],
    "personal_projects": [],
    "skills": ["Java", "SQL", "C++"],
    "certificates": [],
    "honours": [],
    "languages": [],
}

PRED_2 = {
    "personal_info": {
        "full_name": "Trần Thị B",
        "email": "tranb@example.test",
        "phone": "0912345678",  # digits: '0912345678' != '84912345678'
        "github_url": "github.com/tranb_hallucinated",  # FP scalar + hallucination
    },
    "objective": "Tìm kiếm cơ hội mới",  # FP presence
    "education": [],  # FN for school
    "experience": [
        {"company": "Cong ty VNG", "job_title": "Project Manager"},  # Company matches, title wrong
        {"company": "FPT Telecom", "job_title": "DevOps"},  # FP company + hallucination
    ],
    "personal_projects": [{"name": "App Chat"}],  # FP project + hallucination
    "skills": ["Java", "SQL", "Python"],  # TP: Java, SQL; FP: Python; FN: C++
    "certificates": ["Scrum Master"],  # FP cert + hallucination
    "honours": [],
    "languages": [{"language": "Tiếng Nhật"}],  # FP language
}

CV_TEXT_3 = """LÊ VĂN C - Kỹ sư Cầu nối (BrSE)
Email: levanc@example.com
Học vấn: Đại học Quốc Gia TP.HCM
Kỹ năng: Japanese N2, Java
"""

GOLD_3 = {
    "personal_info": {
        "full_name": "Lê Văn C",
        "email": "levanc@example.com",
        "phone": None,
        "github_url": None,
    },
    "objective": None,
    "education": [{"school": "Đại học Quốc Gia TP.HCM"}],
    "experience": [],
    "personal_projects": [],
    "skills": ["Japanese N2", "Java"],
    "certificates": [],
    "honours": [],
    "languages": [],
}

PRED_3 = None  # Failed / unparseable prediction


# ============================================================================
# Unit Tests
# ============================================================================

def test_fuzzy_company_matching():
    """Fuzzy matching: 'Cong ty FPT Software' vs 'Công ty FPT Software' is TP."""
    gold = {"experience": [{"company": "Công ty FPT Software", "job_title": "Developer"}]}
    pred = {"experience": [{"company": "Cong ty FPT Software", "job_title": "Developer"}]}
    score = score_sample(pred, gold, "Công ty FPT Software")

    assert score["experience.company"]["tp"] == 1
    assert score["experience.company"]["fp"] == 0
    assert score["experience.company"]["fn"] == 0


def test_phone_digits_exact_match_rule():
    """Phone comparison is by EXACT digits without prefix normalization.

    '+84 912 345 678' (digits: 84912345678) vs '0912345678' (digits: 0912345678)
    are NOT equal, resulting in correct=False.
    """
    gold = {"personal_info": {"phone": "+84 912 345 678"}}
    pred = {"personal_info": {"phone": "0912345678"}}
    score = score_sample(pred, gold, "Phone: +84 912 345 678")

    phone_score = score["personal_info"]["phone"]
    assert phone_score["gold_present"] is True
    assert phone_score["pred_present"] is True
    assert phone_score["correct"] is False, (
        "Exact digits comparison should not consider +84... and 09... equal"
    )


def test_job_title_matching_on_matched_companies():
    """job_title logic: correct -> TP; wrong -> FP+FN; gold only -> FN; pred only -> FP."""
    # 1. Correct title -> TP
    gold_1 = {"experience": [{"company": "VNG", "job_title": "Senior Python"}]}
    pred_1 = {"experience": [{"company": "VNG", "job_title": "Senior Python"}]}
    s1 = score_sample(pred_1, gold_1, "VNG Senior Python")
    assert s1["experience.job_title"] == {"tp": 1, "fp": 0, "fn": 0}

    # 2. Wrong title on matched company -> FP=1, FN=1
    gold_2 = {"experience": [{"company": "VNG", "job_title": "Frontend Engineer"}]}
    pred_2 = {"experience": [{"company": "VNG", "job_title": "Product Owner"}]}
    s2 = score_sample(pred_2, gold_2, "VNG")
    assert s2["experience.job_title"] == {"tp": 0, "fp": 1, "fn": 1}

    # 3. Gold has title, pred is None -> FN=1
    gold_3 = {"experience": [{"company": "VNG", "job_title": "Backend Lead"}]}
    pred_3 = {"experience": [{"company": "VNG", "job_title": None}]}
    s3 = score_sample(pred_3, gold_3, "VNG Backend Lead")
    assert s3["experience.job_title"] == {"tp": 0, "fp": 0, "fn": 1}

    # 4. Pred has title, gold is None -> FP=1
    gold_4 = {"experience": [{"company": "VNG", "job_title": None}]}
    pred_4 = {"experience": [{"company": "VNG", "job_title": "QA Engineer"}]}
    s4 = score_sample(pred_4, gold_4, "VNG QA Engineer")
    assert s4["experience.job_title"] == {"tp": 0, "fp": 1, "fn": 0}

    # 5. Both None -> ignored (cả hai None thì không tính)
    gold_5 = {"experience": [{"company": "VNG", "job_title": None}]}
    pred_5 = {"experience": [{"company": "VNG", "job_title": None}]}
    s5 = score_sample(pred_5, gold_5, "VNG")
    assert s5["experience.job_title"] == {"tp": 0, "fp": 0, "fn": 0}


def test_skills_set_matching():
    """Skills comparison operates on sets of normalized strings."""
    gold = {"skills": ["Python", "Docker", "C++"]}
    pred = {"skills": ["python", "docker", "Java"]}
    score = score_sample(pred, gold, "CV text")

    # Overlap: {python, docker} -> TP=2
    # Pred extra: {java} -> FP=1
    # Gold extra: {c++} -> FN=1
    assert score["skills"] == {"tp": 2, "fp": 1, "fn": 1}


def test_hallucination_and_gold_ungrounded():
    """Hallucination counting for predicted entities and ungrounded gold values."""
    score_1 = score_sample(PRED_1, GOLD_1, CV_TEXT_1)
    assert score_1["halluc"]["total"] == 8
    assert score_1["halluc"]["ungrounded"] == 0
    assert score_1["gold_ungrounded"]["ungrounded"] == 0

    score_2 = score_sample(PRED_2, GOLD_2, CV_TEXT_2)
    # PRED_2 entities: company (2: VNG, FPT Telecom), project (1: App Chat),
    # cert (1: Scrum Master), email (1: tranb@example.test), github (1: tranb_hallucinated),
    # phone (1: 0912345678). Total = 7
    assert score_2["halluc"]["total"] == 7
    # Ungrounded: FPT Telecom, App Chat, Scrum Master, github, phone (not in digits(cv)) -> 5
    assert score_2["halluc"]["ungrounded"] == 5

    # GOLD_2 silver noise: school 'Đại học Công nghệ' and company 'Viettel' absent from CV_TEXT_2
    assert score_2["gold_ungrounded"]["total"] == 5  # school (1), company (2), email (1), phone (1)
    assert score_2["gold_ungrounded"]["ungrounded"] == 2


def test_pred_none_scores_empty_and_all_fn():
    """When pred is None, scores['valid'] is False and gold items are all FN."""
    score_3 = score_sample(PRED_3, GOLD_3, CV_TEXT_3)

    assert score_3["valid"] is False
    assert score_3["education.school"] == {"tp": 0, "fp": 0, "fn": 1}
    assert score_3["skills"] == {"tp": 0, "fp": 0, "fn": 2}
    assert score_3["personal_info"]["full_name"]["correct"] is False
    assert score_3["personal_info"]["full_name"]["gold_present"] is True
    assert score_3["personal_info"]["full_name"]["pred_present"] is False
    assert score_3["halluc"] == {"total": 0, "ungrounded": 0}


def test_aggregate_micro_f1_and_hand_computed_values():
    """Aggregate metrics match hand-calculated numbers across 3 profiles."""
    s1 = score_sample(PRED_1, GOLD_1, CV_TEXT_1)
    s2 = score_sample(PRED_2, GOLD_2, CV_TEXT_2)
    s3 = score_sample(PRED_3, GOLD_3, CV_TEXT_3)

    latencies = [10.0, 20.0, 30.0]
    agg = aggregate([s1, s2, s3], latencies=latencies)

    # General counts
    assert agg["n"] == 3
    assert pytest.approx(agg["valid_rate"]) == 2 / 3

    # 1. education.school:
    # S1: tp=1, fp=0, fn=0
    # S2: tp=0, fp=0, fn=1
    # S3: tp=0, fp=0, fn=1
    # Total: tp=1, fp=0, fn=2 -> P = 1/1 = 1.0, R = 1/3, F1 = 2*(1/3)/(4/3) = 0.5
    assert agg["education.school"]["tp"] == 1
    assert agg["education.school"]["fp"] == 0
    assert agg["education.school"]["fn"] == 2
    assert pytest.approx(agg["education.school"]["p"]) == 1.0
    assert pytest.approx(agg["education.school"]["r"]) == 1 / 3
    assert pytest.approx(agg["education.school"]["f1"]) == 0.5

    # 2. experience.company:
    # S1: tp=1, fp=0, fn=0
    # S2: tp=1, fp=1, fn=1
    # S3: tp=0, fp=0, fn=0
    # Total: tp=2, fp=1, fn=1 -> P = 2/3, R = 2/3, F1 = 2/3
    assert agg["experience.company"]["tp"] == 2
    assert agg["experience.company"]["fp"] == 1
    assert agg["experience.company"]["fn"] == 1
    assert pytest.approx(agg["experience.company"]["f1"]) == 2 / 3

    # 3. experience.job_title:
    # S1: tp=1, fp=0, fn=0
    # S2: tp=0, fp=1, fn=1
    # S3: tp=0, fp=0, fn=0
    # Total: tp=1, fp=1, fn=1 -> P = 0.5, R = 0.5, F1 = 0.5
    assert agg["experience.job_title"]["tp"] == 1
    assert agg["experience.job_title"]["fp"] == 1
    assert agg["experience.job_title"]["fn"] == 1
    assert pytest.approx(agg["experience.job_title"]["f1"]) == 0.5

    # 4. skills:
    # S1: tp=3, fp=0, fn=0
    # S2: tp=2, fp=1, fn=1
    # S3: tp=0, fp=0, fn=2
    # Total: tp=5, fp=1, fn=3 -> P = 5/6, R = 5/8, F1 = 5/7
    assert agg["skills"]["tp"] == 5
    assert agg["skills"]["fp"] == 1
    assert agg["skills"]["fn"] == 3
    assert pytest.approx(agg["skills"]["p"]) == 5 / 6
    assert pytest.approx(agg["skills"]["r"]) == 5 / 8
    assert pytest.approx(agg["skills"]["f1"]) == 5 / 7

    # 5. personal_projects.name:
    # S1: tp=1, fp=0, fn=0
    # S2: tp=0, fp=1, fn=0
    # S3: tp=0, fp=0, fn=0
    # Total: tp=1, fp=1, fn=0 -> P = 0.5, R = 1.0, F1 = 2/3
    assert agg["personal_projects.name"]["tp"] == 1
    assert agg["personal_projects.name"]["fp"] == 1
    assert agg["personal_projects.name"]["fn"] == 0
    assert pytest.approx(agg["personal_projects.name"]["f1"]) == 2 / 3

    # Scalars
    # full_name: correct: 2, gold_present: 3 -> acc = 2/3
    assert pytest.approx(agg["full_name"]["accuracy"]) == 2 / 3
    assert agg["full_name"]["false_positives"] == 0

    # phone: correct: 1 (S1), gold_present: 2 (S1, S2) -> acc = 0.5
    assert pytest.approx(agg["phone"]["accuracy"]) == 0.5
    assert agg["phone"]["false_positives"] == 0

    # github_url: correct: 1 (S1), gold_present: 1 (S1), FP: 1 (S2) -> acc = 1.0, FP = 1
    assert pytest.approx(agg["github_url"]["accuracy"]) == 1.0
    assert agg["github_url"]["false_positives"] == 1

    # Objective agreement: S1 agree (T/T), S2 disagree (F/T), S3 agree (F/F) -> 2/3
    assert pytest.approx(agg["objective_agreement"]) == 2 / 3

    # Hallucination rate: total=15 (8+7+0), ungrounded=5 (0+5+0) -> 5/15 = 1/3
    assert agg["halluc"]["total"] == 15
    assert agg["halluc"]["ungrounded"] == 5
    assert pytest.approx(agg["hallucination_rate"]) == 1 / 3

    # Gold ungrounded rate: total=15 (8+5+2), ungrounded=2 (0+2+0) -> 2/15
    assert agg["gold_ungrounded"]["total"] == 15
    assert agg["gold_ungrounded"]["ungrounded"] == 2
    assert pytest.approx(agg["gold_ungrounded_rate"]) == 2 / 15

    # Latency: mean=20.0, p50=20.0
    assert agg["latency"] is not None
    assert pytest.approx(agg["latency"]["mean"]) == 20.0
    assert pytest.approx(agg["latency"]["p50"]) == 20.0


def test_dataset_loading_and_stats(tmp_path: Path):
    """Test load_split and load_split_with_stats with JSON string & dict outputs and malformed lines."""
    jsonl_file = tmp_path / "test_split.jsonl"
    lines = [
        # Line 1: output is dict
        json.dumps({"input": "CV text sample 1", "output": {"personal_info": {"full_name": "Nguyen A"}}}),
        # Line 2: output is JSON string
        json.dumps({"input": "CV text sample 2", "output": json.dumps({"personal_info": {"full_name": "Tran B"}})}),
        # Line 3: malformed unparseable output string -> skipped
        json.dumps({"input": "CV text sample 3", "output": "NOT_A_VALID_JSON{"}),
    ]
    jsonl_file.write_text("\n".join(lines), encoding="utf-8")

    samples, skipped = load_split_with_stats(jsonl_file)
    assert len(samples) == 2
    assert skipped == 1

    s1 = samples[0]
    assert isinstance(s1, Sample)
    assert len(s1.id) == 12
    assert s1.cv_text == "CV text sample 1"
    assert s1.gold["personal_info"]["full_name"] == "Nguyen A"
    assert s1.raw["input"] == "CV text sample 1"

    s2 = samples[1]
    assert s2.gold["personal_info"]["full_name"] == "Tran B"

    # load_split returns only the samples list
    direct_samples = load_split(jsonl_file)
    assert len(direct_samples) == 2
    assert direct_samples[0].id == s1.id
