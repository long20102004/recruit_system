"""Weighted scoring for normalized feature values."""

from __future__ import annotations

from collections.abc import Mapping

DEFAULT_WEIGHTS = {"skill": 0.4, "experience": 0.3, "education": 0.15, "context": 0.15}


def validate_weights(weights: Mapping[str, float]) -> dict[str, float]:
    valid = set(DEFAULT_WEIGHTS)
    unknown = set(weights) - valid
    if unknown:
        raise ValueError(f"unknown weight keys: {sorted(unknown)}")
    result = dict(DEFAULT_WEIGHTS)
    result.update({key: float(value) for key, value in weights.items()})
    if any(value < 0 for value in result.values()) or sum(result.values()) <= 0:
        raise ValueError("weights must be non-negative and have a positive total")
    return result


def compute_final_score(features: Mapping[str, float], weights: Mapping[str, float] | None = None) -> float:
    selected = validate_weights(weights or DEFAULT_WEIGHTS)
    total = sum(max(0.0, min(1.0, features[name])) * selected[name] for name in selected)
    return round(total / sum(selected.values()) * 100, 2)
