"""LLM-backed explanation with a deterministic local mode for development."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _local_explanation(score: float, matched: list[str], missing: list[str], features: dict[str, float]) -> dict[str, Any]:
    if missing:
        reasoning = f"Ứng viên đạt {score:.2f} điểm với {len(matched)} kỹ năng phù hợp. "
        reasoning += f"Cần bổ sung hoặc xác minh: {', '.join(missing)}."
    else:
        reasoning = f"Ứng viên đạt {score:.2f} điểm và đáp ứng toàn bộ kỹ năng bắt buộc."
    return {
        "score": score,
        "missing_skills": missing,
        "matched_skills": matched,
        "reasoning": reasoning,
        "feature_scores": features,
    }


def explain_match(
    score: float,
    features: dict[str, float],
    candidate: dict[str, Any],
    jd: dict[str, Any],
    matched: list[str],
    missing: list[str],
) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _local_explanation(score, matched, missing, features)

    from openai import OpenAI

    prompt = (
        "Return only valid JSON with keys missing_skills, matched_skills, reasoning. "
        "Do not change the supplied score. Explain it in 3-4 sentences.\n"
        f"Score: {score}\nFeature scores: {json.dumps(features, ensure_ascii=False)}\n"
        f"Candidate: {json.dumps(candidate, ensure_ascii=False)}\nJD: {json.dumps(jd, ensure_ascii=False)}"
    )
    try:
        response = OpenAI(api_key=api_key).chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("LLM returned an empty explanation")
        parsed = json.loads(content)
        return {
            "score": score,
            "missing_skills": parsed.get("missing_skills", missing),
            "matched_skills": parsed.get("matched_skills", matched),
            "reasoning": parsed["reasoning"],
            "feature_scores": features,
        }
    except Exception as exc:
        logger.warning("LLM explanation unavailable; using deterministic fallback: %s", exc)
        return _local_explanation(score, matched, missing, features)
