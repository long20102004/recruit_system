"""Build the v2 retraining dataset (feature 006).

Run from ai-service/:  python -m training.build_dataset [--hints] [--out data/retrain_v2]

Outputs (JSONL, one CV per line):
  train.jsonl     cleaned silver labels + one entity-swapped copy of each CV
  dev.jsonl       30 CVs held out from the train pool (model selection only)
  val.jsonl       the 99 CVs of feature 003, gold labels unchanged
  val_swap.jsonl  entity-swapped val of feature 003, gold labels unchanged
  summary.json    counts only (no CV content)
Fields: id, input (CV text), output (gold JSON string), prompt, completion.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from app.postprocess.grounding import _is_language_grounded
from app.postprocess.schema import normalize_profile
from app.postprocess.text_match import contains, normalize
from app.services.prompt_v2 import render_prompt, render_target
from eval.dataset import Sample
from eval.swap import build_swap

DEV_SIZE = 30
SEED = 42


def _load(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _sid(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def clean_label(cv_text: str, profile: dict[str, Any], stats: Counter) -> dict:
    """Remove label items that cannot be found in the CV text (same grounding as serving)."""
    p = copy.deepcopy(profile)
    cv_norm = normalize(cv_text)

    def keep_str(field: str, items: list) -> list:
        out = []
        for v in items:
            if not isinstance(v, str) or not contains(cv_norm, v):
                stats[f"removed_ungrounded_{field}"] += 1
            else:
                out.append(v)
        return out

    for field in ("skills", "certificates", "honours"):
        p[field] = keep_str(field, p.get(field) or [])
    langs = []
    for item in p.get("languages") or []:
        if _is_language_grounded(item, cv_norm):
            langs.append(item)
        else:
            stats["removed_ungrounded_languages"] += 1
    p["languages"] = langs
    for exp in p.get("experience") or []:
        bullets = exp.get("description") or []
        kept = [b for b in bullets if isinstance(b, str) and contains(cv_norm, b)]
        stats["removed_ungrounded_experience_bullets"] += len(bullets) - len(kept)
        exp["description"] = kept
    for proj in p.get("personal_projects") or []:
        stack = proj.get("tech_stack") or []
        kept = [t for t in stack if isinstance(t, str) and contains(cv_norm, t)]
        stats["removed_ungrounded_tech_stack"] += len(stack) - len(kept)
        proj["tech_stack"] = kept
    return p


def _record(cv_text: str, gold: dict, gold_raw: str | None, hints_finder) -> dict[str, Any]:
    hints = hints_finder.find(cv_text) if hints_finder else None
    return {
        "id": _sid(cv_text),
        "input": cv_text,
        "output": gold_raw if gold_raw is not None else json.dumps(gold, ensure_ascii=False),
        "prompt": render_prompt(cv_text, hints),
        "completion": render_target(gold),
    }


def _token_counter(tokenizer_path: Path | None):
    if not tokenizer_path or not tokenizer_path.exists():
        return None
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(tokenizer_path))
    return lambda s: len(tok.encode(s).ids)


def build(args: argparse.Namespace) -> dict[str, Any]:
    data = Path(args.data)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stats: Counter = Counter()
    finder = None
    if args.hints:
        from app.kb.candidates import CandidateSkillFinder

        finder = CandidateSkillFinder.from_csv(args.kb_seed)

    val = _load(data / "clean" / "val.jsonl")
    val_swap = _load(data / "val_swap.jsonl")
    val_inputs = {r["input"] for r in val} | {r["input"] for r in val_swap}

    pool, seen = [], set()
    for r in _load(data / "clean" / "silver_dataset.jsonl"):
        if r["input"] in val_inputs or r["input"] in seen:
            stats["pool_skipped_val_or_duplicate"] += 1
            continue
        try:
            label = json.loads(r["output"]) if isinstance(r["output"], str) else r["output"]
        except json.JSONDecodeError:
            stats["pool_skipped_bad_json"] += 1
            continue
        seen.add(r["input"])
        pool.append((r["input"], normalize_profile(label)))
    random.Random(SEED).shuffle(pool)
    dev_pool, train_pool = pool[:DEV_SIZE], pool[DEV_SIZE:]

    def cleaned(items):
        return [(cv, clean_label(cv, gold, stats)) for cv, gold in items]

    train_items = cleaned(train_pool)
    dev_items = cleaned(dev_pool)

    # Augmentation: one entity-swapped copy per train CV; never reuse val_swap names.
    samples = [Sample(id=_sid(cv), cv_text=cv, gold=g, raw={}) for cv, g in train_items]
    avoid = [Sample(id="", cv_text=r["input"], gold=normalize_profile(json.loads(r["output"])), raw={})
             for r in val_swap]
    swapped, swap_summary = build_swap(samples, avoid, seed=SEED + 1)
    for row in swapped:
        if row["input"] not in {cv for cv, _ in train_items}:
            train_items.append((row["input"], json.loads(row["output"])))
            stats["train_augmented"] += 1

    count = _token_counter(Path(args.tokenizer) if args.tokenizer else None)
    splits: dict[str, list[dict]] = {
        "train": [_record(cv, g, None, finder) for cv, g in train_items],
        "dev": [_record(cv, g, None, finder) for cv, g in dev_items],
        "val": [_record(r["input"], normalize_profile(json.loads(r["output"])), r["output"], finder) for r in val],
        "val_swap": [_record(r["input"], normalize_profile(json.loads(r["output"])), r["output"], finder)
                     for r in val_swap],
    }

    lengths: dict[str, Any] = {}
    if count:
        for name, rows in splits.items():
            totals = []
            kept = []
            for row in rows:
                n_prompt, n_comp = count(row["prompt"]), count(row["completion"])
                row["n_prompt_tokens"], row["n_completion_tokens"] = n_prompt, n_comp
                totals.append(n_prompt + n_comp)
                if name in ("train", "dev") and n_prompt + n_comp > args.max_len:
                    stats[f"{name}_dropped_too_long"] += 1
                    continue
                kept.append(row)
            splits[name] = kept
            comps = sorted(r["n_completion_tokens"] for r in rows)
            lengths[name] = {"max_total": max(totals), "mean_completion": round(sum(comps) / len(comps), 1),
                             "max_completion": comps[-1]}

    random.Random(SEED).shuffle(splits["train"])
    for name, rows in splits.items():
        with (out / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "hints": bool(args.hints),
        "max_len": args.max_len,
        "sizes": {k: len(v) for k, v in splits.items()},
        "label_cleaning": dict(sorted(stats.items())),
        "swap": {k: swap_summary[k] for k in ("samples", "names_replaced", "names_not_found")},
        "tokens": lengths,
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default=None, help="default data/retrain_v2 (or data/retrain_v2_hints)")
    ap.add_argument("--hints", action="store_true", help="add KB candidate skills to prompts (variant D)")
    ap.add_argument("--kb-seed", default="kb/seed")
    ap.add_argument("--tokenizer", default="checkpoint-250/tokenizer.json")
    ap.add_argument("--max-len", type=int, default=4096)
    args = ap.parse_args(argv)
    if args.out is None:
        args.out = "data/retrain_v2_hints" if args.hints else "data/retrain_v2"
    print(json.dumps(build(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
