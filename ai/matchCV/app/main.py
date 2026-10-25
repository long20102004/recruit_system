"""FastAPI entrypoint for CV-to-JD matchmaking."""

import time
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

from .explain import explain_match
from .features import extract_features
from .normalize import normalize_candidate, normalize_jd
from .retrieval import hybrid_retrieve
from .scoring import DEFAULT_WEIGHTS, compute_final_score, validate_weights

app = FastAPI(title="Module 2 Matchmaking API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class MatchRequest(BaseModel):
    candidate: dict[str, Any] = Field(default_factory=dict)
    jd: dict[str, Any] = Field(default_factory=dict)
    weights: dict[str, float] | None = None


class BatchMatchRequest(BaseModel):
    jd: dict[str, Any] = Field(default_factory=dict)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    top_k: int = Field(default=50, ge=1)
    weights: dict[str, float] | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "Module 2 Matchmaking API", "docs": "/docs"}


def _run_match(request: MatchRequest, use_llm: bool) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        candidate = normalize_candidate(request.candidate)
        jd = normalize_jd(request.jd)
        features, matched, missing = extract_features(candidate, jd)
        weights = validate_weights(request.weights or DEFAULT_WEIGHTS)
        score = compute_final_score(features, weights)
        if use_llm:
            result = explain_match(score, features, candidate, jd, matched, missing)
        else:
            result = {
                "score": score,
                "missing_skills": missing,
                "matched_skills": matched,
                "reasoning": (
                    f"Điểm tự động: {score:.2f}/100. "
                    f"Khớp {len(matched)}/{len(jd['required_skills'])} kỹ năng yêu cầu."
                ),
                "feature_scores": features,
            }
        result["weights_used"] = weights
        result["processing_time_ms"] = round((time.perf_counter() - started) * 1000, 1)
        return result
    except (TypeError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/match")
def match(request: MatchRequest) -> dict[str, Any]:
    return _run_match(request, use_llm=True)


@app.post("/match/no-llm")
def match_without_llm(request: MatchRequest) -> dict[str, Any]:
    return _run_match(request, use_llm=False)


@app.post("/match_batch")
def match_batch(request: BatchMatchRequest) -> dict[str, Any]:
    try:
        normalized_jd = normalize_jd(request.jd)
        retrieval_candidates = [
            {
                "id": candidate.get("candidate_id", candidate.get("id", f"cv_{index + 1:03d}")),
                "text": _candidate_text(candidate),
                "candidate": candidate,
            }
            for index, candidate in enumerate(request.candidates)
        ]
        retrieved = hybrid_retrieve(
            _jd_text(request.jd),
            retrieval_candidates,
            top_k=min(request.top_k, len(retrieval_candidates)),
        )
        weights = validate_weights(request.weights or DEFAULT_WEIGHTS)
        top_k = []
        for item in retrieved:
            normalized_candidate = normalize_candidate(item["candidate"])
            features, matched, missing = extract_features(normalized_candidate, normalized_jd)
            top_k.append(
                {
                    "candidate_id": str(item["id"]),
                    "retrieval_score": item["retrieval_score"],
                    "score": compute_final_score(features, weights),
                    "feature_scores": features,
                    "matched_skills": matched,
                    "missing_skills": missing,
                }
            )
        return {"jd": normalized_jd, "top_k": top_k}
    except (TypeError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _candidate_text(candidate: dict[str, Any]) -> str:
    values = [
        candidate.get("raw_context"),
        candidate.get("summary"),
        candidate.get("name"),
        candidate.get("skills"),
        candidate.get("job_titles"),
        candidate.get("certificates"),
    ]
    return " ".join(str(value) for value in values if value)


def _jd_text(jd: dict[str, Any]) -> str:
    values = [jd.get("title"), jd.get("description"), jd.get("context"), jd.get("required_skills"), jd.get("skills")]
    return " ".join(str(value) for value in values if value)
