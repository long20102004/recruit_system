"""Prediction runner for evaluation splits via the CV extraction HTTP service."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import Any, Sequence
import urllib.error
import urllib.request


def run_predictions(
    samples: Sequence[Any],
    base_url: str,
    run_dir: str | Path,
    timeout: float = 600.0,
) -> dict[str, dict[str, Any]]:
    """Run extraction requests for samples against the service and cache predictions.

    Args:
        samples: Sequence of Sample objects (having .id and .cv_text).
        base_url: Base URL of the extraction service.
        run_dir: Path to directory where predictions.jsonl is saved.
        timeout: HTTP request timeout in seconds.

    Returns:
        Dictionary mapping sample id to its prediction record.
    """
    run_path = Path(run_dir)
    run_path.mkdir(parents=True, exist_ok=True)
    pred_path = run_path / "predictions.jsonl"

    existing_records: dict[str, dict[str, Any]] = {}
    if pred_path.exists():
        with pred_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if "id" in rec:
                        existing_records[str(rec["id"])] = rec
                except Exception:
                    continue

    url = f"{base_url.rstrip('/')}/api/v1/extract-cv"
    total_samples = len(samples)

    for i, sample in enumerate(samples, start=1):
        sample_id = str(getattr(sample, "id", None) or sample.get("id"))
        if sample_id in existing_records:
            continue

        cv_text = getattr(sample, "cv_text", None) or sample.get("cv_text", "")
        payload = json.dumps({"cv_text": cv_text}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        t0 = time.perf_counter()
        status = 0
        data = None

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", 200)
                resp_bytes = resp.read().decode("utf-8")
                try:
                    res_json = json.loads(resp_bytes)
                    data = res_json.get("data") if isinstance(res_json, dict) else None
                except Exception:
                    data = None
        except urllib.error.HTTPError as e:
            status = e.code
            data = None
        except Exception:
            status = 0
            data = None

        latency_s = time.perf_counter() - t0

        record: dict[str, Any] = {
            "id": sample_id,
            "status": status,
            "data": data,
            "latency_s": round(latency_s, 4),
        }

        with pred_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()

        existing_records[sample_id] = record
        print(f"[{i}/{total_samples}] {sample_id} {status} {latency_s:.2f}s", flush=True)

    return existing_records


def main() -> None:
    parser = argparse.ArgumentParser(description="Run predictions against CV extraction service")
    parser.add_argument("--split", required=True, help="Path to split JSONL file")
    parser.add_argument("--run", required=True, help="Run directory to store predictions.jsonl")
    parser.add_argument("--base-url", required=True, help="Base URL of extraction service")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of samples to run")
    parser.add_argument("--timeout", type=float, default=600.0, help="HTTP timeout in seconds (default: 600)")
    args = parser.parse_args()

    from eval.dataset import load_split

    samples = load_split(args.split)
    if args.limit is not None:
        samples = samples[: args.limit]

    run_predictions(
        samples=samples,
        base_url=args.base_url,
        run_dir=args.run,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
