"""Build the v4 retraining dataset (feature 013).

Run from ai-service/:  python -m training.build_dataset_v4 [--out data/retrain_v4]

Same prompt and label conventions as v3 (``prompt_v3``); every CV text is the column-aware
"layout" text the backend now serves (feature 011), so train and serve see the same text.

Sources (all CV data stays under git-ignored data/):
  generated  data/synth_v3/{r0,r5}/          fictional profiles, layouts L1-L10 (2 passes)
             data/synth_v4/r11/             same profiles, new layouts L11-L14 (feature 013)
             text = <pass>/text_xy/<id>.json (layout extractor); label = profile after the
             layout's printing rules, grounded in that text
  real       data/real_test/train_real_v4.jsonl   31 real CVs, v3 labels re-aligned to layout text, x3 (2 entity swaps)
  synthetic  data/clean/silver_dataset.jsonl      250 old synthetic CVs (plain text), v3 conventions
Held out:   test_real = 19 real test CVs (layout text, gold v3) + CV 57 (user's expected JSON);
            val / val_swap (feature 003, regression).
Outputs: train / dev / val / val_swap / test_real .jsonl + summary.json (counts only).
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
from training.synth.render import ground_label

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


def generated_label(profile: dict, text: str, stats: Counter) -> dict:
    grounded, dropped = ground_label(profile, text)
    stats.update({f"generated_dropped:{k}": v for k, v in dropped.items()})
    p = normalize_profile(grounded)
    p["languages"] = [x for x in p["languages"] if not is_programming_language(x.get("language"))]
    return p


def _generated_passes(data: Path, extra: tuple[str, ...] = ()) -> list[tuple[str, dict, str]]:
    """(id, label source row, layout text) for every generated render with layout text."""
    out = []
    profiles = {}
    for f in sorted((data / "synth_v3" / "profiles").glob("*.jsonl")):
        for p in _load(f):
            profiles[p["id"]] = p
    for folder in (data / "synth_v3" / "r0", data / "synth_v3" / "r5"):
        for r in _load(folder / "rendered.jsonl"):
            t = folder / "text_xy" / f"{r['id']}.json"
            if t.exists():
                out.append((r["id"], {"layout": r["layout"], "level": r["level"],
                                      "profile": profiles[r["id"]]["profile"]}, json.load(open(t))["text"]))
    for folder in (data / "synth_v4" / "r11", *(data / e for e in extra)):
        if not (folder / "labels.jsonl").exists():
            continue
        for r in _load(folder / "labels.jsonl"):
            t = folder / "text_xy" / f"{r['id']}.json"
            if t.exists():
                label = json.loads(r["output"]) if isinstance(r["output"], str) else r["output"]
                out.append((r["id"], {"layout": r["layout"], "level": r["level"], "profile": label},
                            json.load(open(t))["text"]))
    return out


def build(args: argparse.Namespace) -> dict:
    data, out = Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    stats: Counter = Counter()

    test = _load(data / "real_test" / "gold_011" / "test_real_layout.jsonl")
    cv57 = data / "real_test" / "gold_011" / "cv57_layout.jsonl"
    if cv57.exists():
        test += _load(cv57)
    val = _load(data / "clean" / "val.jsonl")
    val_swap = _load(data / "val_swap.jsonl")
    held_texts = [r["input"][:3000] for r in test + val + val_swap]

    def leaks(text: str) -> bool:
        head = text[:3000]
        return any(fuzz.ratio(head, h) > 70 for h in held_texts)

    # generated: hold out whole profiles for dev (every layout of a dev profile goes to dev)
    gen = _generated_passes(data, tuple(getattr(args, "extra_generated", ()) or ()))
    # variants of a profile ("<id>.m", "<id>.s", "<id>.t", feature 014) follow their base profile
    base = lambda pid: pid.split(".")[0]  # noqa: E731
    ids = sorted({base(g[0]) for g in gen})
    rng.shuffle(ids)
    dev_ids = set(ids[:DEV_GENERATED_PROFILES])
    train, dev = [], []
    for pid, meta, text in gen:
        label = generated_label(meta["profile"], text, stats)
        rec = _record(text, label, f"generated:{meta['layout']}:{meta['level']}")
        in_dev = base(pid) in dev_ids
        (dev if in_dev else train).append(rec)
        stats["generated_dev" if in_dev else "generated_train"] += 1
        if "." in pid:
            stats[f"generated_variant_{pid.rsplit('.', 1)[1]}{'_dev' if in_dev else ''}"] += 1

    # real CVs (layout text): original + entity swaps
    real = [r for r in _load(data / "real_test" / "train_real_v4.jsonl")
            if not leaks(r["input"]) or stats.update(["real_dropped_leak"])]
    samples = [Sample(id=_sid(r["input"]), cv_text=r["input"], gold=json.loads(r["output"]), raw={}) for r in real]
    for r in real:
        train.append(_record(r["input"], json.loads(r["output"]), "real"))
        stats["real"] += 1
    avoid = [Sample(id="", cv_text=r["input"], gold=normalize_profile(json.loads(r["output"])), raw={}) for r in val_swap]
    for k in range(getattr(args, "real_swaps", REAL_SWAPS)):
        swapped, _ = build_swap(samples, avoid, seed=SEED + 10 + k)
        for row in swapped:
            train.append(_record(row["input"], normalize_profile(json.loads(row["output"])), "real_swap"))
            stats["real_swap"] += 1

    # old synthetic, v3 conventions (plain text, unchanged)
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
               "train_generated_by_layout": Counter(r["source"].split(":")[1] for r in splits["train"]
                                                    if r["source"].startswith("generated")),
               "stats": dict(sorted(stats.items())), "tokens": lengths, "max_len": args.max_len,
               "hints": False, "text": "layout (feature 011)"}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="data/retrain_v4")
    ap.add_argument("--tokenizer", default="checkpoint-250/tokenizer.json")
    ap.add_argument("--max-len", type=int, default=4096)
    print(json.dumps(build(ap.parse_args(argv)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
