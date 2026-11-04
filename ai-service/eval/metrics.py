"""Metric computation and aggregation for CV profile extraction evaluation."""

from __future__ import annotations

import re
import statistics
from typing import Any

from rapidfuzz import fuzz

from app.postprocess.schema import normalize_profile
from app.postprocess.text_match import (
    contains,
    digits,
    find_span,
    normalize,
    normalize_with_map,
)

__all__ = ["score_sample", "aggregate"]


def _clean_github(url: str | None) -> str:
    """Normalize GitHub URL: drop http(s)://, www., and trailing slashes."""
    if not url:
        return ""
    s = str(url).strip()
    s = re.sub(r"^https?://", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^www\.", "", s, flags=re.IGNORECASE)
    s = s.rstrip("/")
    return normalize(s)


def _match_entities_greedy(
    pred_items: list[str | None],
    gold_items: list[str | None],
    threshold: float = 90.0,
) -> tuple[int, int, int, list[tuple[int, int, float]]]:
    """Greedy 1-to-1 matching using rapidfuzz token_set_ratio.

    Pairs are matched in descending order of similarity down to threshold.
    Returns (tp, fp, fn, matched_pairs) where each pair is (pred_idx, gold_idx, score).
    """
    valid_preds = [
        (i, normalize(p))
        for i, p in enumerate(pred_items)
        if p and isinstance(p, str) and normalize(p)
    ]
    valid_golds = [
        (j, normalize(g))
        for j, g in enumerate(gold_items)
        if g and isinstance(g, str) and normalize(g)
    ]

    candidates: list[tuple[float, int, int]] = []
    for p_idx, p_norm in valid_preds:
        for g_idx, g_norm in valid_golds:
            score = fuzz.token_set_ratio(p_norm, g_norm)
            if score >= threshold:
                candidates.append((score, p_idx, g_idx))

    # Sort descending by score; tie-break on lower indices for stability
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))

    matched_p: set[int] = set()
    matched_g: set[int] = set()
    matched_pairs: list[tuple[int, int, float]] = []

    for score, p_idx, g_idx in candidates:
        if p_idx not in matched_p and g_idx not in matched_g:
            matched_p.add(p_idx)
            matched_g.add(g_idx)
            matched_pairs.append((p_idx, g_idx, score))

    tp = len(matched_pairs)
    fp = len(valid_preds) - tp
    fn = len(valid_golds) - tp
    return tp, fp, fn, matched_pairs


def _match_set(pred_items: list[Any], gold_items: list[Any]) -> dict[str, int]:
    """Compare normalized string sets and return {tp, fp, fn}."""
    pred_set = {
        normalize(str(item))
        for item in pred_items
        if item is not None and str(item).strip() and normalize(str(item))
    }
    gold_set = {
        normalize(str(item))
        for item in gold_items
        if item is not None and str(item).strip() and normalize(str(item))
    }
    tp = len(pred_set & gold_set)
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)
    return {"tp": tp, "fp": fp, "fn": fn}


def _count_ungrounded(profile: dict, cv_text: str) -> dict[str, int]:
    """Count total and ungrounded entities in profile against cv_text.

    Entities verified:
    - education.school: find_span is None
    - experience.company: find_span is None
    - personal_projects.name: find_span is None
    - certificates: find_span is None
    - honours: find_span is None
    - email: not contains(cv_norm, email)
    - github_url: not contains(cv_norm, _clean_github(url))
    - phone: len(digits) >= 8 and digits not in digits(cv_text)
    """
    total = 0
    ungrounded = 0

    if not cv_text or not isinstance(cv_text, str):
        cv_text = ""

    cv_norm, cv_map = normalize_with_map(cv_text)
    cv_digs = digits(cv_text)

    # 1. education.school
    for edu in profile.get("education", []):
        if not isinstance(edu, dict):
            continue
        school = edu.get("school")
        if school and isinstance(school, str) and normalize(school):
            total += 1
            if find_span(school, cv_text, cv_norm=cv_norm, cv_map=cv_map) is None:
                ungrounded += 1

    # 2. experience.company
    for exp in profile.get("experience", []):
        if not isinstance(exp, dict):
            continue
        comp = exp.get("company")
        if comp and isinstance(comp, str) and normalize(comp):
            total += 1
            if find_span(comp, cv_text, cv_norm=cv_norm, cv_map=cv_map) is None:
                ungrounded += 1

    # 3. personal_projects.name
    for proj in profile.get("personal_projects", []):
        if not isinstance(proj, dict):
            continue
        pname = proj.get("name")
        if pname and isinstance(pname, str) and normalize(pname):
            total += 1
            if find_span(pname, cv_text, cv_norm=cv_norm, cv_map=cv_map) is None:
                ungrounded += 1

    # 4. certificates
    for cert in profile.get("certificates", []):
        if cert and isinstance(cert, str) and normalize(cert):
            total += 1
            if find_span(cert, cv_text, cv_norm=cv_norm, cv_map=cv_map) is None:
                ungrounded += 1

    # 5. honours
    for hon in profile.get("honours", []):
        if hon and isinstance(hon, str) and normalize(hon):
            total += 1
            if find_span(hon, cv_text, cv_norm=cv_norm, cv_map=cv_map) is None:
                ungrounded += 1

    # 6. email
    pinfo = profile.get("personal_info") or {}
    email = pinfo.get("email")
    if email and isinstance(email, str) and normalize(email):
        total += 1
        if not contains(cv_norm, email):
            ungrounded += 1

    # 7. github_url
    gh = pinfo.get("github_url")
    if gh and isinstance(gh, str):
        gh_clean = _clean_github(gh)
        if gh_clean:
            total += 1
            if not contains(cv_norm, gh_clean):
                ungrounded += 1

    # 8. phone
    phone = pinfo.get("phone")
    if phone is not None:
        p_digs = digits(str(phone))
        if len(p_digs) >= 8:
            total += 1
            if p_digs not in cv_digs:
                ungrounded += 1

    return {"total": total, "ungrounded": ungrounded}


def score_sample(pred: dict | None, gold: dict, cv_text: str) -> dict:
    """Score a single sample prediction against gold labels.

    If pred is None or not a dict, scores['valid'] is False and evaluated
    against an empty profile (normalize_profile(None)).
    """
    valid = isinstance(pred, dict)
    norm_pred = normalize_profile(pred) if valid else normalize_profile(None)
    norm_gold = normalize_profile(gold)

    # 1. Scalars (personal_info)
    p_info_pred = norm_pred.get("personal_info") or {}
    p_info_gold = norm_gold.get("personal_info") or {}

    # full_name
    fn_g = normalize(p_info_gold.get("full_name"))
    fn_p = normalize(p_info_pred.get("full_name"))
    score_full_name = {
        "gold_present": bool(fn_g),
        "pred_present": bool(fn_p),
        "correct": bool(fn_g and fn_p and fn_g == fn_p),
    }

    # email
    em_g = normalize(p_info_gold.get("email"))
    em_p = normalize(p_info_pred.get("email"))
    score_email = {
        "gold_present": bool(em_g),
        "pred_present": bool(em_p),
        "correct": bool(em_g and em_p and em_g == em_p),
    }

    # phone (digits exact matching)
    ph_g = digits(p_info_gold.get("phone"))
    ph_p = digits(p_info_pred.get("phone"))
    score_phone = {
        "gold_present": bool(ph_g),
        "pred_present": bool(ph_p),
        "correct": bool(ph_g and ph_p and ph_g == ph_p),
    }

    # github_url
    gh_g = _clean_github(p_info_gold.get("github_url"))
    gh_p = _clean_github(p_info_pred.get("github_url"))
    score_github = {
        "gold_present": bool(gh_g),
        "pred_present": bool(gh_p),
        "correct": bool(gh_g and gh_p and gh_g == gh_p),
    }

    # 2. Entity lists: education.school, experience.company, personal_projects.name
    # education.school
    pred_schools = [
        e.get("school") for e in norm_pred.get("education", []) if isinstance(e, dict)
    ]
    gold_schools = [
        e.get("school") for e in norm_gold.get("education", []) if isinstance(e, dict)
    ]
    sch_tp, sch_fp, sch_fn, _ = _match_entities_greedy(
        pred_schools, gold_schools, threshold=90.0
    )
    score_school = {"tp": sch_tp, "fp": sch_fp, "fn": sch_fn}

    # experience.company and experience.job_title
    pred_exp = [e for e in norm_pred.get("experience", []) if isinstance(e, dict)]
    gold_exp = [e for e in norm_gold.get("experience", []) if isinstance(e, dict)]
    pred_comps = [e.get("company") for e in pred_exp]
    gold_comps = [e.get("company") for e in gold_exp]
    comp_tp, comp_fp, comp_fn, matched_exp_pairs = _match_entities_greedy(
        pred_comps, gold_comps, threshold=90.0
    )
    score_company = {"tp": comp_tp, "fp": comp_fp, "fn": comp_fn}

    # experience.job_title: evaluated over matched company pairs
    title_tp = 0
    title_fp = 0
    title_fn = 0
    for p_idx, g_idx, _ in matched_exp_pairs:
        p_title = pred_exp[p_idx].get("job_title")
        g_title = gold_exp[g_idx].get("job_title")
        p_t_norm = normalize(p_title) if p_title else ""
        g_t_norm = normalize(g_title) if g_title else ""

        if not p_t_norm and not g_t_norm:
            # cả hai None thì không tính
            continue
        if g_t_norm and not p_t_norm:
            title_fn += 1
        elif p_t_norm and not g_t_norm:
            title_fp += 1
        else:
            if p_t_norm == g_t_norm or fuzz.token_set_ratio(p_t_norm, g_t_norm) >= 90:
                title_tp += 1
            else:
                title_fp += 1
                title_fn += 1
    score_job_title = {"tp": title_tp, "fp": title_fp, "fn": title_fn}

    # personal_projects.name
    pred_projs = [
        p.get("name") for p in norm_pred.get("personal_projects", []) if isinstance(p, dict)
    ]
    gold_projs = [
        p.get("name") for p in norm_gold.get("personal_projects", []) if isinstance(p, dict)
    ]
    proj_tp, proj_fp, proj_fn, _ = _match_entities_greedy(
        pred_projs, gold_projs, threshold=90.0
    )
    score_proj_name = {"tp": proj_tp, "fp": proj_fp, "fn": proj_fn}

    # 3. Set lists: skills, certificates, honours, languages (item['language'])
    score_skills = _match_set(norm_pred.get("skills", []), norm_gold.get("skills", []))
    score_certs = _match_set(
        norm_pred.get("certificates", []), norm_gold.get("certificates", [])
    )
    score_honours = _match_set(norm_pred.get("honours", []), norm_gold.get("honours", []))

    pred_lang_names = [
        item.get("language")
        for item in norm_pred.get("languages", [])
        if isinstance(item, dict) and item.get("language")
    ]
    gold_lang_names = [
        item.get("language")
        for item in norm_gold.get("languages", [])
        if isinstance(item, dict) and item.get("language")
    ]
    score_languages = _match_set(pred_lang_names, gold_lang_names)

    # 4. objective
    obj_g = normalize(norm_gold.get("objective"))
    obj_p = normalize(norm_pred.get("objective"))
    score_obj = {
        "gold_present": bool(obj_g),
        "pred_present": bool(obj_p),
    }

    # 5. Hallucination and gold ungrounded
    score_halluc = _count_ungrounded(norm_pred, cv_text)
    score_gold_ungrounded = _count_ungrounded(norm_gold, cv_text)

    return {
        "valid": valid,
        "personal_info": {
            "full_name": score_full_name,
            "email": score_email,
            "phone": score_phone,
            "github_url": score_github,
        },
        "personal_info.full_name": score_full_name,
        "personal_info.email": score_email,
        "personal_info.phone": score_phone,
        "personal_info.github_url": score_github,
        "education.school": score_school,
        "experience.company": score_company,
        "experience.job_title": score_job_title,
        "personal_projects.name": score_proj_name,
        "skills": score_skills,
        "certificates": score_certs,
        "honours": score_honours,
        "languages": score_languages,
        "languages.language": score_languages,
        "objective": score_obj,
        "halluc": score_halluc,
        "gold_ungrounded": score_gold_ungrounded,
    }


def aggregate(
    scores: list[dict],
    latencies: list[float] | None = None,
) -> dict:
    """Aggregate per-sample scores and latencies into dataset-level metrics."""
    n = len(scores)
    if n == 0:
        return {
            "n": 0,
            "valid_rate": 0.0,
            "hallucination_rate": None,
            "gold_ungrounded_rate": None,
            "objective_agreement": None,
            "latency": None,
            "fields": {},
            "scalars": {},
        }

    valid_count = sum(1 for s in scores if s.get("valid", False))
    valid_rate = valid_count / n

    # Micro P/R/F1 for list fields
    list_field_keys = (
        "education.school",
        "experience.company",
        "experience.job_title",
        "personal_projects.name",
        "skills",
        "certificates",
        "honours",
        "languages.language",
    )

    fields_summary: dict[str, Any] = {}
    for key in list_field_keys:
        tp_total = sum(s[key]["tp"] for s in scores)
        fp_total = sum(s[key]["fp"] for s in scores)
        fn_total = sum(s[key]["fn"] for s in scores)

        p = tp_total / (tp_total + fp_total) if (tp_total + fp_total) > 0 else None
        r = tp_total / (tp_total + fn_total) if (tp_total + fn_total) > 0 else None
        if p is not None and r is not None:
            if (p + r) > 0:
                f1 = (2 * p * r) / (p + r)
            else:
                f1 = 0.0
        else:
            f1 = None

        fields_summary[key] = {
            "p": p,
            "r": r,
            "f1": f1,
            "tp": tp_total,
            "fp": fp_total,
            "fn": fn_total,
        }

    # Also provide alias "languages" pointing to "languages.language"
    fields_summary["languages"] = fields_summary["languages.language"]

    # Scalars accuracy and false positives
    scalar_field_names = ("full_name", "email", "phone", "github_url")
    scalars_summary: dict[str, Any] = {}
    for fname in scalar_field_names:
        gold_pres = sum(1 for s in scores if s["personal_info"][fname]["gold_present"])
        correct = sum(1 for s in scores if s["personal_info"][fname]["correct"])
        pred_pres = sum(1 for s in scores if s["personal_info"][fname]["pred_present"])
        fp = sum(
            1
            for s in scores
            if s["personal_info"][fname]["pred_present"]
            and not s["personal_info"][fname]["gold_present"]
        )
        acc = (correct / gold_pres) if gold_pres > 0 else None
        scalars_summary[f"personal_info.{fname}"] = {
            "accuracy": acc,
            "correct": correct,
            "gold_present": gold_pres,
            "pred_present": pred_pres,
            "false_positives": fp,
        }
        scalars_summary[fname] = scalars_summary[f"personal_info.{fname}"]

    # Objective agreement
    agree_count = sum(
        1
        for s in scores
        if s["objective"]["gold_present"] == s["objective"]["pred_present"]
    )
    objective_agreement = agree_count / n

    # Hallucination rate & gold ungrounded rate
    total_halluc = sum(s["halluc"]["total"] for s in scores)
    ungrounded_halluc = sum(s["halluc"]["ungrounded"] for s in scores)
    halluc_rate = (ungrounded_halluc / total_halluc) if total_halluc > 0 else 0.0

    total_gold = sum(s["gold_ungrounded"]["total"] for s in scores)
    ungrounded_gold = sum(s["gold_ungrounded"]["ungrounded"] for s in scores)
    gold_ungrounded_rate = (ungrounded_gold / total_gold) if total_gold > 0 else 0.0

    # Latencies
    latency_summary: dict[str, float] | None = None
    if latencies:
        valid_lats = [float(x) for x in latencies if x is not None]
        if valid_lats:
            mean_lat = statistics.mean(valid_lats)
            p50_lat = statistics.median(valid_lats)
            try:
                if len(valid_lats) >= 2:
                    p95_lat = statistics.quantiles(
                        valid_lats, n=100, method="inclusive"
                    )[94]
                else:
                    p95_lat = valid_lats[0]
            except Exception:
                sorted_lats = sorted(valid_lats)
                idx = int(0.95 * (len(sorted_lats) - 1))
                p95_lat = sorted_lats[idx]
            latency_summary = {
                "mean": mean_lat,
                "p50": p50_lat,
                "p95": p95_lat,
            }

    result: dict[str, Any] = {
        "n": n,
        "valid_rate": valid_rate,
        "hallucination_rate": halluc_rate,
        "gold_ungrounded_rate": gold_ungrounded_rate,
        "objective_agreement": objective_agreement,
        "latency": latency_summary,
        "fields": fields_summary,
        "scalars": scalars_summary,
        "halluc": {
            "total": total_halluc,
            "ungrounded": ungrounded_halluc,
            "rate": halluc_rate,
        },
        "gold_ungrounded": {
            "total": total_gold,
            "ungrounded": ungrounded_gold,
            "rate": gold_ungrounded_rate,
        },
        "objective": {
            "agreement": objective_agreement,
            "agree_count": agree_count,
            "total": n,
        },
    }

    # Expose list fields and scalar fields directly at top-level
    for k, v in fields_summary.items():
        result[k] = v
    for k, v in scalars_summary.items():
        result[k] = v

    return result
