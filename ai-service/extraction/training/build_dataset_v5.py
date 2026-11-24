"""Build the v5 retraining dataset (feature 014) = dataset v4 + three shapes v4 got wrong.

Run from ai-service/:  python -m training.build_dataset_v5 [--out data/retrain_v5]

Same prompt (prompt_v3), labels and layout text as v4 (training.build_dataset_v4), plus:
  data/synth_v5/rv   130 profile variants (training.synth.variants), layouts L1-L15:
                     70 with 4-6 consecutive short jobs + many projects, 60 students with no jobs
  data/synth_v5/r15  70 profiles in layout L15: "<end date> <title>" under the company, start date
                     at the bottom of the entry (the two-column timeline of real CVs)
  real CVs           x4 instead of x3 (3 entity swaps) so real text keeps its weight.
Held-out splits are the v4 ones (test_real 20, val, val_swap); dev profiles are held out with all
their variants. Outputs: train / dev / val / val_swap / test_real .jsonl + summary.json (counts only).
"""

from __future__ import annotations

import argparse
import json

from training.build_dataset_v4 import build


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="data/retrain_v5")
    ap.add_argument("--tokenizer", default="checkpoint-250/tokenizer.json")
    ap.add_argument("--max-len", type=int, default=4096)
    ap.add_argument("--real-swaps", type=int, default=3)
    ap.add_argument("--extra-generated", nargs="*", default=["synth_v5/rv", "synth_v5/r15"])
    summary = build(ap.parse_args(argv))
    summary["dataset"] = "v5 (feature 014)"
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
