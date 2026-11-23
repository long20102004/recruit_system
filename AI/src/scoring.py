"""Core scoring: BERTScore/fast + coverage + Ridge — dùng chung CLI và API."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import numpy as np

from .features import FEATURE_COLUMNS, bertscore_prf, build_feature_row, lexical_prf
from .io_utils import OUTPUT, questions_by_id
from .rubric import evaluate_rubric


@lru_cache(maxsize=4)
def load_calibration(mode: str) -> dict[str, Any]:
    path = OUTPUT / f"calibration_{mode}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Chưa có {path}. Chạy: python -m src.train_calibration --mode {mode}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def clear_calibration_cache() -> None:
    load_calibration.cache_clear()


def predict_score(feat: dict[str, Any], calib: dict[str, Any]) -> float:
    coefs = calib["coefficients"]
    intercept = float(calib["intercept"])
    raw = intercept + sum(float(coefs[c]) * float(feat[c]) for c in FEATURE_COLUMNS)
    return float(np.clip(raw, 0, 10))


def combine_model_and_rubric(model_score: float, rubric: dict[str, Any]) -> float:
    """Blend a global score with criterion coverage and cap keyword stuffing."""
    coverage = float(rubric["coverage_score"])
    score = min(0.5 * float(model_score) + 5 * coverage, 10 * coverage + 2)
    if rubric.get("keyword_only"):
        score = min(score, 1.0)
    return float(np.clip(score, 0, 10))


def build_comment(covered: list[str], missing: list[str], score: float) -> str:
    if score >= 8.5 and not missing:
        return "Câu trả lời đầy đủ các ý theo tiêu chí."
    if missing and covered:
        return (
            "Đã nêu được một số ý chính. "
            f"Nên bổ sung: {', '.join(missing)}."
        )
    if missing and not covered:
        return (
            "Câu trả lời chưa khớp rõ tiêu chí. "
            f"Hãy nêu: {', '.join(missing)}."
        )
    return "Câu trả lời ổn, có thể làm rõ thêm bằng ví dụ thực tế."


def evaluate_question(
    *,
    answer: str,
    question: dict[str, Any],
    mode: str = "fast",
    model_type: str | None = None,
    device: str | None = None,
    include_debug: bool = False,
) -> dict[str, Any]:
    """Chấm 1 câu với object câu hỏi đầy đủ (reference + criteria)."""
    answer = (answer or "").strip()
    if not answer:
        raise ValueError("answer trống")
    if "reference_answer" not in question or "criteria" not in question:
        raise ValueError("question cần có reference_answer và criteria")

    if mode not in {"fast", "bertscore", "finetune"}: raise ValueError("Unsupported scoring mode")
    if mode == "finetune":
        return _evaluate_finetune(answer, question, include_debug=include_debug)
    calib = load_calibration(mode)
    ref = question["reference_answer"]

    if mode == "fast":
        p, r, f1 = lexical_prf(answer, ref)
    else:
        mt = model_type or calib.get("bert_model_type") or "bert-base-multilingual-cased"
        P, R, F1 = bertscore_prf([answer], [ref], model_type=mt, device=device)
        p, r, f1 = float(P[0]), float(R[0]), float(F1[0])

    feat = build_feature_row(answer, question, p, r, f1)
    rubric = evaluate_rubric(answer, question["criteria"], mode,
        model_type or calib.get("bert_model_type") or "bert-base-multilingual-cased", device)
    calibrated = predict_score(feat, calib)
    score = combine_model_and_rubric(calibrated, rubric)
    covered = rubric["covered_labels"]
    missing = rubric["missing_labels"]

    result: dict[str, Any] = {
        "question_id": question.get("id"),
        "predicted_score": round(score, 2),
        "score_scale": "0-10",
        "covered_points": covered,
        "missing_points": missing,
        "comment": build_comment(covered, missing, score),
        "model_version": str(calib.get("model_version", "unknown")) + "+evidence-v3",
        "mode": mode,
        "bertscore_precision": round(p,4) if mode == "bertscore" else None,
        "bertscore_recall": round(r,4) if mode == "bertscore" else None,
        "bertscore_f1": round(f1,4) if mode == "bertscore" else None,
        "coverage_score": round(rubric["coverage_score"],4),
        "criterion_results": rubric["criterion_results"],
        "label_source": calib.get("label_source", "unknown"),
    }

    if include_debug:
        result["debug"] = {
            "bert_P": feat["bert_P"],
            "bert_R": feat["bert_R"],
            "bert_F1": feat["bert_F1"],
            "coverage_score": round(rubric["coverage_score"],4),
            "keyword_coverage_score": feat["coverage_score"],
            "length_norm": feat["length_norm"],
            "covered_keys": [c["key"] for c in rubric["criterion_results"] if c["status"]=="covered"],
            "missing_keys": [c["key"] for c in rubric["criterion_results"] if c["status"]!="covered"],
        }
    return result


def _evaluate_finetune(answer: str, question: dict[str, Any], include_debug: bool) -> dict[str, Any]:
    """Fine-tuned regressor supplies the global score. Rubric still supplies evidence."""
    from .regressor import model_version, predict_regression

    model_score = predict_regression(
        str(question.get("question") or ""),
        answer,
        question.get("reference_answer"),
    )
    rubric = evaluate_rubric(answer, question["criteria"], "finetune", None, None)
    score = combine_model_and_rubric(model_score, rubric)
    result: dict[str, Any] = {
        "question_id": question.get("id"),
        "predicted_score": round(score, 2),
        "score_scale": "0-10",
        "covered_points": rubric["covered_labels"],
        "missing_points": rubric["missing_labels"],
        "comment": build_comment(rubric["covered_labels"], rubric["missing_labels"], score),
        "model_version": model_version() + "+evidence-v3",
        "mode": "finetune",
        "bertscore_precision": None,
        "bertscore_recall": None,
        "bertscore_f1": None,
        "coverage_score": round(rubric["coverage_score"], 4),
        "criterion_results": rubric["criterion_results"],
        "label_source": "assistant_graded+synthetic_rubric",
    }
    if include_debug:
        result["debug"] = {
            "finetune_score": round(model_score, 4),
            "coverage_score": result["coverage_score"],
        }
    return result


def evaluate_by_id(
    question_id: str,
    answer: str,
    mode: str = "fast",
    **kwargs: Any,
) -> dict[str, Any]:
    qmap = questions_by_id()
    if question_id not in qmap:
        raise KeyError(f"Không có question_id={question_id}. Có: {list(qmap)}")
    return evaluate_question(
        answer=answer,
        question=qmap[question_id],
        mode=mode,
        **kwargs,
    )
