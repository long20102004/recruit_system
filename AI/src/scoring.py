"""Core scoring: BERTScore/fast + coverage + Ridge — dùng chung CLI và API."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import numpy as np

from .features import FEATURE_COLUMNS, bertscore_prf, build_feature_row, lexical_prf
from .io_utils import OUTPUT, questions_by_id


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

    calib = load_calibration(mode)
    ref = question["reference_answer"]

    if mode == "fast":
        p, r, f1 = lexical_prf(answer, ref)
    else:
        mt = model_type or calib.get("bert_model_type") or "bert-base-multilingual-cased"
        P, R, F1 = bertscore_prf([answer], [ref], model_type=mt, device=device)
        p, r, f1 = float(P[0]), float(R[0]), float(F1[0])

    feat = build_feature_row(answer, question, p, r, f1)
    score = predict_score(feat, calib)
    covered = feat["covered_labels"]
    missing = feat["missing_labels"]

    result: dict[str, Any] = {
        "question_id": question.get("id"),
        "predicted_score": round(score, 2),
        "score_scale": "0-10",
        "covered_points": covered,
        "missing_points": missing,
        "comment": build_comment(covered, missing, score),
        "model_version": calib.get("model_version"),
        "mode": mode,
    }

    if include_debug:
        result["debug"] = {
            "bert_P": feat["bert_P"],
            "bert_R": feat["bert_R"],
            "bert_F1": feat["bert_F1"],
            "coverage_score": feat["coverage_score"],
            "length_norm": feat["length_norm"],
            "covered_keys": feat["covered_keys"],
            "missing_keys": feat["missing_keys"],
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
