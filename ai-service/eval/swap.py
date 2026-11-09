"""Entity-swapped evaluation split builder for CV extraction.

Replaces company and school names in validation CVs and gold profiles
with fictitious names never seen in training CVs, to test whether models
read CV context or rely on memorised entity names.
"""

from __future__ import annotations

import argparse
import copy
import json
import random
from pathlib import Path
from typing import Any

from app.postprocess.schema import normalize_profile
from app.postprocess.text_match import normalize, normalize_with_map

try:
    from eval.dataset import Sample, load_split
except ImportError:
    import hashlib
    from dataclasses import dataclass, field

    @dataclass
    class Sample:
        id: str
        cv_text: str
        gold: dict[str, Any]
        raw: dict[str, Any] = field(default_factory=dict)

    def load_split(path: str | Path) -> list[Sample]:
        samples: list[Sample] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                cv_text = raw.get("input", "")
                output_raw = raw.get("output", "{}")
                if isinstance(output_raw, str):
                    try:
                        gold_raw = json.loads(output_raw)
                    except Exception:
                        gold_raw = {}
                elif isinstance(output_raw, dict):
                    gold_raw = output_raw
                else:
                    gold_raw = {}
                gold = normalize_profile(gold_raw)
                sample_id = hashlib.sha1(cv_text.encode("utf-8")).hexdigest()[:12]
                samples.append(Sample(id=sample_id, cv_text=cv_text, gold=gold, raw=raw))
        return samples

COMPANY_PREFIXES: tuple[str, ...] = ("Công ty TNHH", "Công ty Cổ phần")
COMPANY_SUFFIXES: tuple[str, ...] = ("Tech", "Solutions", "Software", "Digital")
SCHOOL_PREFIX: str = "Trường Đại học"

SYLLABLE_POOL: tuple[str, ...] = (
    "Vanh", "Thuy", "Loc", "Khai", "Minh", "Phong", "Khang", "Trieu",
    "Quang", "Duy", "Nhat", "Hieu", "Lam", "Son", "Giang", "Hai",
    "Binh", "Phuoc", "Tuan", "Kien", "Thinh", "Vinh", "Dan", "Quyen",
    "Bach", "Hoang", "Long", "Viet", "Chau", "An", "Phuc", "Thanh",
)


def _generate_word(rng: random.Random) -> str:
    s1 = rng.choice(SYLLABLE_POOL)
    s2 = rng.choice(SYLLABLE_POOL)
    return f"{s1.capitalize()}{s2.lower()}"


def _generate_fictitious_name(
    entity_type: str,
    rng: random.Random,
    train_names: set[str],
    cv_norm: str,
    used_in_cv: set[str],
) -> str:
    for _ in range(10000):
        w1 = _generate_word(rng)
        w2 = _generate_word(rng)
        while w2 == w1:
            w2 = _generate_word(rng)

        if entity_type == "company":
            prefix = rng.choice(COMPANY_PREFIXES)
            suffix = rng.choice(COMPANY_SUFFIXES)
            name = f"{prefix} {w1} {w2} {suffix}"
        else:
            name = f"{SCHOOL_PREFIX} {w1} {w2}"

        norm = normalize(name)
        if norm in train_names:
            continue
        if norm in cv_norm:
            continue
        if norm in used_in_cv:
            continue

        used_in_cv.add(norm)
        return name

    raise RuntimeError(f"Could not generate unique fictitious {entity_type} name after 10000 attempts.")


def _collect_train_names(train_samples: list[Sample]) -> set[str]:
    train_names: set[str] = set()
    for s in train_samples:
        gold = s.gold if isinstance(s.gold, dict) else {}
        for exp in gold.get("experience", []):
            if isinstance(exp, dict) and exp.get("company"):
                norm = normalize(exp["company"])
                if norm:
                    train_names.add(norm)
        for edu in gold.get("education", []):
            if isinstance(edu, dict) and edu.get("school"):
                norm = normalize(edu["school"])
                if norm:
                    train_names.add(norm)
    return train_names


def _find_word_boundary_spans(cv_norm: str, target_norm: str) -> list[tuple[int, int]]:
    if not cv_norm or not target_norm:
        return []
    spans: list[tuple[int, int]] = []
    pos = 0
    t_len = len(target_norm)
    cv_len = len(cv_norm)
    while True:
        idx = cv_norm.find(target_norm, pos)
        if idx == -1:
            break
        before_ok = (idx == 0 or not cv_norm[idx - 1].isalnum())
        after_ok = (idx + t_len == cv_len or not cv_norm[idx + t_len].isalnum())
        if before_ok and after_ok:
            spans.append((idx, idx + t_len))
        pos = idx + 1
    return spans


def build_swap(
    samples: list[Sample],
    train_samples: list[Sample],
    seed: int = 42,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build entity-swapped evaluation split replacing gold company and school names.

    Args:
        samples: Validation split samples to swap.
        train_samples: Training split samples to extract known train entity names.
        seed: Random seed for reproducible fictitious name generation.

    Returns:
        tuple containing:
            - list of new JSONL line dicts (instruction, input, output).
            - summary dict with replacement counts.
    """
    rng = random.Random(seed)
    train_names = _collect_train_names(train_samples)

    total_names_replaced = 0
    total_occurrences_replaced = 0
    total_names_not_found = 0

    per_type_stats = {
        "company": {"names_replaced": 0, "occurrences_replaced": 0, "names_not_found": 0},
        "school": {"names_replaced": 0, "occurrences_replaced": 0, "names_not_found": 0},
    }

    swapped_rows: list[dict[str, Any]] = []

    for sample in samples:
        cv_text = sample.cv_text
        cv_norm, cv_map = normalize_with_map(cv_text)
        gold = sample.gold if isinstance(sample.gold, dict) else {}

        # Collect unique target names per type, keeping order of appearance
        company_targets: list[str] = []
        for exp in gold.get("experience", []):
            if isinstance(exp, dict) and exp.get("company"):
                comp = str(exp["company"]).strip()
                if comp and comp not in company_targets:
                    company_targets.append(comp)

        school_targets: list[str] = []
        for edu in gold.get("education", []):
            if isinstance(edu, dict) and edu.get("school"):
                sch = str(edu["school"]).strip()
                if sch and sch not in school_targets:
                    school_targets.append(sch)

        cv_new_names: dict[str, str] = {}
        cv_name_found: dict[str, bool] = {}
        used_in_cv: set[str] = set()

        raw_replacement_spans: list[tuple[int, int, str, str]] = []

        # Process company names
        for comp in company_targets:
            norm_name = normalize(comp)
            if len(norm_name) < 4:
                continue

            if norm_name in cv_name_found:
                continue

            spans = _find_word_boundary_spans(cv_norm, norm_name)
            if not spans:
                cv_name_found[norm_name] = False
                per_type_stats["company"]["names_not_found"] += 1
                total_names_not_found += 1
                continue

            cv_name_found[norm_name] = True
            new_name = _generate_fictitious_name("company", rng, train_names, cv_norm, used_in_cv)
            cv_new_names[norm_name] = new_name
            per_type_stats["company"]["names_replaced"] += 1
            total_names_replaced += 1

            for s, e in spans:
                orig_s = cv_map[s]
                orig_e = cv_map[e - 1] + 1
                raw_replacement_spans.append((orig_s, orig_e, new_name, "company"))

        # Process school names
        for sch in school_targets:
            norm_name = normalize(sch)
            if len(norm_name) < 4:
                continue

            if norm_name in cv_name_found:
                continue

            spans = _find_word_boundary_spans(cv_norm, norm_name)
            if not spans:
                cv_name_found[norm_name] = False
                per_type_stats["school"]["names_not_found"] += 1
                total_names_not_found += 1
                continue

            cv_name_found[norm_name] = True
            if norm_name in cv_new_names:
                new_name = cv_new_names[norm_name]
            else:
                new_name = _generate_fictitious_name("school", rng, train_names, cv_norm, used_in_cv)
                cv_new_names[norm_name] = new_name
            per_type_stats["school"]["names_replaced"] += 1
            total_names_replaced += 1

            for s, e in spans:
                orig_s = cv_map[s]
                orig_e = cv_map[e - 1] + 1
                raw_replacement_spans.append((orig_s, orig_e, new_name, "school"))

        # Resolve any overlapping spans (longer spans take precedence)
        accepted_spans: list[tuple[int, int, str, str]] = []
        for span in sorted(raw_replacement_spans, key=lambda x: (x[1] - x[0]), reverse=True):
            s, e, _, _ = span
            overlaps = any(not (e <= a_s or s >= a_e) for a_s, a_e, _, _ in accepted_spans)
            if not overlaps:
                accepted_spans.append(span)

        for _, _, _, ent_type in accepted_spans:
            total_occurrences_replaced += 1
            per_type_stats[ent_type]["occurrences_replaced"] += 1

        # Replace spans in CV text from right to left
        accepted_spans.sort(key=lambda x: x[0], reverse=True)
        new_cv_text = cv_text
        for s, e, new_name, _ in accepted_spans:
            new_cv_text = new_cv_text[:s] + new_name + new_cv_text[e:]

        # Update gold profile
        new_gold = copy.deepcopy(gold)
        for exp in new_gold.get("experience", []):
            if isinstance(exp, dict) and exp.get("company"):
                norm_c = normalize(exp["company"])
                if norm_c in cv_new_names and cv_name_found.get(norm_c, False):
                    exp["company"] = cv_new_names[norm_c]

        for edu in new_gold.get("education", []):
            if isinstance(edu, dict) and edu.get("school"):
                norm_s = normalize(edu["school"])
                if norm_s in cv_new_names and cv_name_found.get(norm_s, False):
                    edu["school"] = cv_new_names[norm_s]

        # Prepare JSONL output row
        new_raw = dict(sample.raw) if getattr(sample, "raw", None) else {}
        if "instruction" not in new_raw:
            new_raw["instruction"] = ""
        new_raw["input"] = new_cv_text
        new_raw["output"] = json.dumps(new_gold, ensure_ascii=False)
        swapped_rows.append(new_raw)

    summary = {
        "samples": len(samples),
        "names_replaced": total_names_replaced,
        "occurrences_replaced": total_occurrences_replaced,
        "names_not_found": total_names_not_found,
        "per_type": per_type_stats,
    }

    return swapped_rows, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build entity-swapped evaluation split.")
    parser.add_argument("--val", required=True, help="Path to val.jsonl")
    parser.add_argument("--train", required=True, help="Path to train.jsonl")
    parser.add_argument("--out", required=True, help="Path to output val_swap.jsonl")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    val_samples = load_split(args.val)
    train_samples = load_split(args.train)

    swapped_rows, summary = build_swap(val_samples, train_samples, seed=args.seed)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for row in swapped_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    if out_path.name.endswith(".jsonl"):
        summary_path = out_path.with_name(out_path.name[:-6] + ".summary.json")
    else:
        summary_path = out_path.with_name(out_path.stem + ".summary.json")

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
