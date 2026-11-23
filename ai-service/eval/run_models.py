"""Run one GGUF model over evaluation splits through the serving code (feature 010).

    python -m eval.run_models --gguf merged_model/model-v3-q4_k_m.gguf --prompt-version v3 \
        --split test_real=data/retrain_v3/test_real.jsonl --out data/runs/v3 [--n-gpu-layers -1]

Same path as the API: prompt of the given version, llama.cpp greedy, loop guard, JSON parse with
fragment merge (feature 008). Post-processing is NOT applied here: the scoring harness applies it
(variant B). Writes <out>/<split>/predictions.jsonl in the eval.predict format; resumable.
stdout: counts only (no CV content).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gguf", required=True)
    ap.add_argument("--prompt-version", required=True, choices=["v1", "v2", "v3"])
    ap.add_argument("--split", action="append", required=True, help="name=path.jsonl (repeatable)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-gpu-layers", type=int, default=0)
    ap.add_argument("--n-ctx", type=int, default=8192)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)

    # config reads the prompt version at import time
    os.environ["PROMPT_VERSION"] = args.prompt_version
    from llama_cpp import Llama

    from app.services import model_loader
    from app.services.generator import generate_cv_result
    from app.utils.json_parse import extract_json
    from app.utils.text import clean_cv_text

    state = model_loader.state
    state.llm = Llama(args.gguf, n_ctx=args.n_ctx, n_gpu_layers=args.n_gpu_layers, verbose=False)
    state.engine, state.context_tokens = "llama_cpp", args.n_ctx

    for spec in args.split:
        name, path = spec.split("=", 1)
        rows = [json.loads(line) for line in Path(path).open(encoding="utf-8") if line.strip()]
        if args.limit:
            rows = rows[: args.limit]
        out_dir = Path(args.out) / name
        out_dir.mkdir(parents=True, exist_ok=True)
        pred_path = out_dir / "predictions.jsonl"
        done = set()
        if pred_path.exists():
            done = {json.loads(line)["id"] for line in pred_path.open(encoding="utf-8") if line.strip()}
        todo = [r for r in rows if r["id"] not in done]
        print(f"[{name}] {len(rows)} rows, {len(done)} done, {len(todo)} to run", flush=True)
        with pred_path.open("a", encoding="utf-8") as f:
            for i, row in enumerate(todo, 1):
                t0 = time.time()
                status, data, tokens, reason = 200, None, None, None
                try:
                    gen = generate_cv_result(clean_cv_text(row["input"]))
                    tokens, reason = gen.output_tokens, gen.reason
                    data = extract_json(gen.text)
                    if not isinstance(data, dict):
                        status, data = 502, None
                except Exception as e:  # noqa: BLE001 — record the failure type only
                    status, data, reason = 500, None, type(e).__name__
                dt = round(time.time() - t0, 2)
                f.write(json.dumps({"id": row["id"], "status": status, "latency_s": dt, "output_tokens": tokens,
                                    "truncated": reason, "data": data}, ensure_ascii=False) + "\n")
                f.flush()
                if i % 10 == 0 or i == len(todo):
                    print(f"[{name}] {i}/{len(todo)} last={dt}s status={status}", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
