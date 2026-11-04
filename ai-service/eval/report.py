"""Report generator comparing evaluation variants across splits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from eval.dataset import load_split
from eval.metrics import aggregate, score_sample
from eval.variants import VARIANTS


def _resolve_field(data: Any, path: str) -> Any:
    """Traverse nested dict or direct key access."""
    if not isinstance(data, dict):
        return None
    if path in data:
        return data[path]
    parts = path.split(".")
    curr = data
    for part in parts:
        if isinstance(curr, dict) and part in curr:
            curr = curr[part]
        else:
            return None
    return curr


def _get_metric_val(agg: dict[str, Any], field_path: str, metric_name: str | None = None) -> float | int | None:
    """Extract metric value tolerantly from aggregated results."""
    val = _resolve_field(agg, field_path)
    if val is None:
        if field_path == "languages":
            val = _resolve_field(agg, "languages.language")
        elif field_path == "languages.language":
            val = _resolve_field(agg, "languages")
        elif field_path == "latency.mean":
            val = agg.get("latency_mean")
        elif field_path == "latency.p95":
            val = agg.get("latency_p95")

    if val is None:
        return None
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, dict) and metric_name:
        for k in (metric_name, metric_name.lower(), metric_name.upper(), "val", "value"):
            if k in val and isinstance(val[k], (int, float)):
                return val[k]
        if metric_name.lower() == "accuracy":
            for k in ("acc", "Accuracy", "ACC"):
                if k in val and isinstance(val[k], (int, float)):
                    return val[k]
    return None


METRIC_SPECS: list[tuple[str, str, str | None, str | None]] = [
    ("n", "Sample count (n)", None, None),
    ("missing", "Missing predictions", None, None),
    ("valid_rate", "Schema validity rate", "valid_rate", None),
    ("hallucination_rate", "Hallucination rate", "hallucination_rate", None),
    ("gold_ungrounded_rate", "Gold ungrounded rate", "gold_ungrounded_rate", None),
    ("exp_company_f1", "experience.company (F1)", "experience.company", "f1"),
    ("edu_school_f1", "education.school (F1)", "education.school", "f1"),
    ("proj_name_f1", "personal_projects.name (F1)", "personal_projects.name", "f1"),
    ("exp_title_f1", "experience.job_title (F1)", "experience.job_title", "f1"),
    ("skills_f1", "skills (F1)", "skills", "f1"),
    ("certificates_f1", "certificates (F1)", "certificates", "f1"),
    ("honours_f1", "honours (F1)", "honours", "f1"),
    ("languages_f1", "languages (F1)", "languages", "f1"),
    ("full_name_acc", "personal_info.full_name (Acc)", "personal_info.full_name", "accuracy"),
    ("email_acc", "personal_info.email (Acc)", "personal_info.email", "accuracy"),
    ("phone_acc", "personal_info.phone (Acc)", "personal_info.phone", "accuracy"),
    ("github_url_acc", "personal_info.github_url (Acc)", "personal_info.github_url", "accuracy"),
    ("latency_mean", "Latency mean (s)", "latency.mean", None),
    ("latency_p95", "Latency p95 (s)", "latency.p95", None),
]


def build_report(
    run_dir: str | Path,
    split_paths: Sequence[str | Path],
    variants: Sequence[str] = ("A", "B"),
) -> dict[str, Any]:
    """Score predictions, aggregate metrics and build markdown/json reports."""
    run_path = Path(run_dir)
    run_path.mkdir(parents=True, exist_ok=True)
    pred_path = run_path / "predictions.jsonl"

    pred_records: dict[str, dict[str, Any]] = {}
    if pred_path.exists():
        with pred_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if "id" in rec:
                        pred_records[str(rec["id"])] = rec
                except Exception:
                    continue

    all_scores_entries: list[dict[str, Any]] = []
    report_data: dict[str, Any] = {
        "run_dir": str(run_path),
        "splits": {},
    }

    # Structure to hold columns for report table: (split_name, variant) -> (n, missing, agg)
    col_results: dict[tuple[str, str], dict[str, Any]] = {}
    col_headers: list[str] = []

    for split_item in split_paths:
        split_path = Path(split_item)
        split_name = split_path.stem
        samples = load_split(split_path)

        if split_name not in report_data["splits"]:
            report_data["splits"][split_name] = {}

        for var_name in variants:
            if var_name not in VARIANTS:
                raise ValueError(f"Unknown variant '{var_name}'. Available: {list(VARIANTS.keys())}")

            var_fn = VARIANTS[var_name]
            scores: list[dict[str, Any]] = []
            latencies: list[float] = []
            missing_count = 0

            for sample in samples:
                sample_id = str(getattr(sample, "id", None) or sample.get("id"))
                cv_text = getattr(sample, "cv_text", None) or sample.get("cv_text", "")
                gold = getattr(sample, "gold", None) if hasattr(sample, "gold") else sample.get("gold")

                rec = pred_records.get(sample_id)
                if rec is None:
                    missing_count += 1
                    continue

                if rec.get("status") == 200:
                    pred_data = var_fn(rec.get("data"), cv_text)
                else:
                    pred_data = None

                sc = score_sample(pred_data, gold, cv_text)
                scores.append(sc)
                all_scores_entries.append({
                    "id": sample_id,
                    "split": split_name,
                    "variant": var_name,
                    "scores": sc,
                })

                lat = rec.get("latency_s")
                if isinstance(lat, (int, float)):
                    latencies.append(float(lat))

            agg = aggregate(scores, latencies=latencies) if scores else {}
            report_data["splits"][split_name][var_name] = {
                "n": len(scores),
                "missing": missing_count,
                "metrics": agg,
            }

            key = (split_name, var_name)
            col_results[key] = {
                "n": len(scores),
                "missing": missing_count,
                "agg": agg,
            }
            col_headers.append(f"{split_name} / {var_name}")

    # Write scores.jsonl
    scores_path = run_path / "scores.jsonl"
    with scores_path.open("w", encoding="utf-8") as f:
        for item in all_scores_entries:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # Build Markdown table
    header_line = "| Metric | " + " | ".join(col_headers) + " |"
    sep_line = "| :--- | " + " | ".join([":---:"] * len(col_headers)) + " |"
    rows: list[str] = [header_line, sep_line]

    for metric_id, row_label, field_path, sub_metric in METRIC_SPECS:
        row_cells: list[str] = []
        for split_item in split_paths:
            s_name = Path(split_item).stem
            for var_name in variants:
                res = col_results.get((s_name, var_name), {})
                if metric_id == "n":
                    row_cells.append(str(res.get("n", 0)))
                elif metric_id == "missing":
                    row_cells.append(str(res.get("missing", 0)))
                else:
                    agg = res.get("agg", {})
                    val = _get_metric_val(agg, field_path or "", sub_metric)
                    if isinstance(val, (int, float)):
                        row_cells.append(f"{val:.3f}")
                    else:
                        row_cells.append("-")
        rows.append(f"| {row_label} | " + " | ".join(row_cells) + " |")

    report_md = "# Evaluation Report\n\n" + "\n".join(rows) + "\n"

    # Write report.json and report.md
    with (run_path / "report.json").open("w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    with (run_path / "report.md").open("w", encoding="utf-8") as f:
        f.write(report_md)

    # Print report.md to console
    print(report_md, flush=True)

    return report_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Build evaluation report comparing variants across splits")
    parser.add_argument("--run", required=True, help="Run directory containing predictions.jsonl")
    parser.add_argument("--splits", nargs="+", required=True, help="Paths to split JSONL files")
    parser.add_argument("--variants", nargs="+", default=["A", "B"], help="Variants to evaluate (default: A B)")
    args = parser.parse_args()

    build_report(
        run_dir=args.run,
        split_paths=args.splits,
        variants=tuple(args.variants),
    )


if __name__ == "__main__":
    main()
