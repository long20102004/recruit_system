"""Build the v3 retraining dataset (feature 007).

Run from ai-service/:  python -m training.build_dataset_v3 [--out data/retrain_v3]

Sources (all CV data stays under git-ignored data/):
  generated  data/synth_v3/r0, r5/rendered.jsonl   fictional profiles in 10 real-like layouts, 2 layouts each;
             label = the profile itself (ground truth, also for two-column text that PDFBox interleaves)
  real       data/real_test/train_real_v3.jsonl     real CVs, old labels aligned to PDFBox text; x3 (original + 2 entity swaps)
  synthetic  data/clean/silver_dataset.jsonl        sample of the old synthetic CVs, v3 conventions applied
Held out:   data/real_test/test_v3.jsonl (20 real CVs, gold) and the feature 003 val / val_swap (regression).
Outputs: train.jsonl, dev.jsonl, val.jsonl, val_swap.jsonl, test_real.jsonl, summary.json (counts only).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

from app.postprocess.schema import normalize_profile
from app.services.prompt_v3 import render_prompt, render_target
from eval.dataset import Sample
from eval.swap import build_swap
from training.real_align import align_label, is_programming_language

SEED = 42
DEV_GENERATED_PROFILES = 15
DEV_SYNTHETIC = 15
OLD_SYNTHETIC = 250
REAL_SWAPS = 2


def _load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _sid(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def _record(cv: str, label: dict, source: str, raw_output: str | None = None) -> dict:
    return {"id": _sid(cv), "source": source, "input": cv,
            "output": raw_output if raw_output is not None else json.dumps(label, ensure_ascii=False),
            "prompt": render_prompt(cv), "completion": render_target(label)}


def generated_label(profile: dict) -> dict:
    p = normalize_profile(profile)
    # v3 convention: programming languages never in languages (guard against generator slips)
    p["languages"] = [x for x in p["languages"] if not is_programming_language(x.get("language"))]
    return p


def build(args: argparse.Namespace) -> dict:
    data, out = Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    stats: Counter = Counter()

    test = _load(data / "real_test" / "test_v3.jsonl")
    val = _load(data / "clean" / "val.jsonl")
    val_swap = _load(data / "val_swap.jsonl")
    held_texts = [r["input"][:3000] for r in test + val + val_swap]

    def leaks(text: str) -> bool:
        head = text[:3000]
        return any(fuzz.ratio(head, h) > 70 for h in held_texts)

    # generated: profile id -> truth label; hold out some profiles for dev
    profiles = {}
    for f in sorted((data / "synth_v3" / "profiles").glob("*.jsonl")):
        for p in _load(f):
            profiles[p["id"]] = p
    rendered = [r for d in ("r0", "r5") for r in _load(data / "synth_v3" / d / "rendered.jsonl")]
    ids = sorted({r["id"] for r in rendered})
    rng.shuffle(ids)
    dev_ids = set(ids[:DEV_GENERATED_PROFILES])
    train, dev = [], []
    for r in rendered:
        label = generated_label(profiles[r["id"]]["profile"])
        rec = _record(r["input"], label, f"generated:{r['layout']}:{r['level']}")
        (dev if r["id"] in dev_ids else train).append(rec)
        stats["generated_dev" if r["id"] in dev_ids else "generated_train"] += 1

    # real CVs: original + entity swaps
    real = _load(data / "real_test" / "train_real_v3.jsonl")
    real = [r for r in real if not leaks(r["input"]) or stats.update(["real_dropped_leak"])]
    samples = [Sample(id=_sid(r["input"]), cv_text=r["input"], gold=json.loads(r["output"]), raw={}) for r in real]
    for r in real:
        train.append(_record(r["input"], json.loads(r["output"]), "real"))
        stats["real"] += 1
    avoid = [Sample(id="", cv_text=r["input"], gold=normalize_profile(json.loads(r["output"])), raw={}) for r in val_swap]
    for k in range(REAL_SWAPS):
        swapped, _ = build_swap(samples, avoid, seed=SEED + 10 + k)
        for row in swapped:
            train.append(_record(row["input"], normalize_profile(json.loads(row["output"])), "real_swap"))
            stats["real_swap"] += 1

    # old synthetic, v3 conventions
    val_inputs = {r["input"] for r in val + val_swap}
    pool = [r for r in _load(data / "clean" / "silver_dataset.jsonl") if r["input"] not in val_inputs]
    rng.shuffle(pool)
    for i, r in enumerate(pool[:OLD_SYNTHETIC + DEV_SYNTHETIC]):
        if leaks(r["input"]):
            stats["synthetic_dropped_leak"] += 1
            continue
        label = align_label(r["input"], json.loads(r["output"]), stats)
        (dev if i < DEV_SYNTHETIC else train).append(_record(r["input"], label, "synthetic"))
        stats["synthetic_dev" if i < DEV_SYNTHETIC else "synthetic_train"] += 1

    def eval_split(rows: list[dict], source: str) -> list[dict]:
        return [_record(r["input"], normalize_profile(json.loads(r["output"])), source, r["output"]) for r in rows]

    splits = {"train": train, "dev": dev, "val": eval_split(val, "val"),
              "val_swap": eval_split(val_swap, "val_swap"), "test_real": eval_split(test, "test_real")}

    lengths = {}
    if args.tokenizer and Path(args.tokenizer).exists():
        from tokenizers import Tokenizer

        tok = Tokenizer.from_file(args.tokenizer)
        for name, rows in splits.items():
            kept, totals = [], []
            for row in rows:
                n = len(tok.encode(row["prompt"] + row["completion"]).ids)
                totals.append(n)
                if name in ("train", "dev") and n > args.max_len:
                    stats[f"{name}_dropped_too_long"] += 1
                    continue
                kept.append(row)
            splits[name] = kept
            lengths[name] = {"max_total": max(totals), "mean_total": round(sum(totals) / len(totals))}

    rng.shuffle(splits["train"])
    for name, rows in splits.items():
        with (out / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    summary = {"sizes": {k: len(v) for k, v in splits.items()},
               "train_by_source": Counter(r["source"].split(":")[0] for r in splits["train"]),
               "train_generated_by_level": Counter(r["source"].split(":")[2] for r in splits["train"]
                                                   if r["source"].startswith("generated")),
               "stats": dict(sorted(stats.items())), "tokens": lengths, "max_len": args.max_len, "hints": False}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="data/retrain_v3")
    ap.add_argument("--tokenizer", default="checkpoint-250/tokenizer.json")
    ap.add_argument("--max-len", type=int, default=4096)
    print(json.dumps(build(ap.parse_args(argv)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
