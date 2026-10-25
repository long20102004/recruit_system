"""Simple, explainable Phase 1 feature calculations."""

from __future__ import annotations

from typing import Any

from .embeddings import cosine_similarity
from .graph import default_skill_graph, graph_match_score, skill_to_node_id

PARTIAL_MATCH_THRESHOLD = 0.75
EDUCATION_LEVELS = {
    "": 0,
    "không yêu cầu": 0,
    "high school": 1,
    "trung học": 1,
    "associate": 2,
    "cao đẳng": 2,
    "bachelor": 3,
    "cử nhân": 3,
    "đại học": 3,
    "master": 4,
    "thạc sĩ": 4,
    "phd": 5,
    "tiến sĩ": 5,
}


def skill_match_details(candidate: dict[str, Any], jd: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    candidate_skills = set(candidate.get("skills", []))
    graph = default_skill_graph()
    matched, missing = [], []
    points = 0.0
    for required in jd.get("required_skills", []):
        best = max((score_skill_pair(graph, skill, required) for skill in candidate_skills), default=0.0)
        if best >= PARTIAL_MATCH_THRESHOLD:
            matched.append(required)
        points += best
        if best < PARTIAL_MATCH_THRESHOLD:
            missing.append(required)
    total = len(jd.get("required_skills", []))
    return (points / total if total else 1.0), matched, missing


def score_skill_pair(
    graph: Any,
    skill_cv: str,
    skill_jd: str,
    w_graph: float = 0.6,
    w_semantic: float = 0.4,
) -> float:
    node_cv = skill_to_node_id(skill_cv)
    node_jd = skill_to_node_id(skill_jd)
    semantic_score = cosine_similarity(skill_cv, skill_jd)
    if not node_cv or not node_jd:
        return semantic_score
    graph_score = graph_match_score(graph, node_cv, node_jd)
    return max(0.0, min(1.0, w_graph * graph_score + w_semantic * semantic_score))


def score_skill(candidate: dict[str, Any], jd: dict[str, Any]) -> float:
    return skill_match_details(candidate, jd)[0]


def score_experience(candidate: dict[str, Any], jd: dict[str, Any]) -> float:
    minimum = jd.get("min_experience_years", 0.0)
    years_score = 1.0 if minimum == 0 else min(candidate.get("experience_years", 0.0) / minimum, 1.0)
    required_title = jd.get("required_title", "")
    if not required_title:
        return years_score
    title_score = max((cosine_similarity(title, required_title) for title in candidate.get("job_titles", [])), default=0.0)
    return min(1.0, years_score * 0.7 + title_score * 0.3)


def score_education(candidate: dict[str, Any], jd: dict[str, Any]) -> float:
    required = EDUCATION_LEVELS.get(jd.get("education", ""), 0)
    actual = EDUCATION_LEVELS.get(candidate.get("education", ""), 0)
    if required == 0:
        return 1.0
    if actual >= required:
        return 1.0
    if actual == required - 1:
        return 0.5
    return 0.0


def score_context(candidate: dict[str, Any], jd: dict[str, Any]) -> float:
    candidate_context = candidate.get("raw_context", "")
    jd_context = jd.get("context", "")
    if not candidate_context or not jd_context:
        return 0.5
    return cosine_similarity(candidate_context, jd_context)


def extract_features(candidate: dict[str, Any], jd: dict[str, Any]) -> tuple[dict[str, float], list[str], list[str]]:
    skill, matched, missing = skill_match_details(candidate, jd)
    scores = {
        "skill": skill,
        "experience": score_experience(candidate, jd),
        "education": score_education(candidate, jd),
        "context": score_context(candidate, jd),
    }
    return scores, matched, missing
