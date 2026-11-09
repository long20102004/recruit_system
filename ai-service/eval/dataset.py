"""Dataset loading utilities for evaluation harness."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from app.postprocess.schema import normalize_profile

__all__ = ["Sample", "load_split", "load_split_with_stats"]


@dataclass(frozen=True)
class Sample:
    id: str
    cv_text: str
    gold: dict
    raw: dict


def load_split_with_stats(path: str | Path) -> tuple[list[Sample], int]:
    """Read a JSONL split and return (samples, skipped_count).

    Each line in the JSONL has:
    - input: CV text
    - output: JSON string or dict containing profile

    Rules:
    - id = sha1(input.encode("utf-8")).hexdigest()[:12]
    - gold = normalize_profile(parsed_output)
    - raw = original line dict (for swap to rewrite)
    - Unparseable output lines are skipped and counted.
    """
    samples: list[Sample] = []
    skipped = 0
    path_obj = Path(path)

    with path_obj.open("r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                raw_item = json.loads(line_str)
            except Exception:
                skipped += 1
                continue

            if not isinstance(raw_item, dict):
                skipped += 1
                continue

            cv_text = raw_item.get("input", "")
            if not isinstance(cv_text, str):
                cv_text = str(cv_text) if cv_text is not None else ""

            output_val = raw_item.get("output")
            if isinstance(output_val, str):
                try:
                    parsed_output = json.loads(output_val)
                except Exception:
                    skipped += 1
                    continue
            elif isinstance(output_val, dict):
                parsed_output = output_val
            else:
                skipped += 1
                continue

            if not isinstance(parsed_output, dict):
                skipped += 1
                continue

            sample_id = hashlib.sha1(cv_text.encode("utf-8")).hexdigest()[:12]
            gold = normalize_profile(parsed_output)
            samples.append(Sample(id=sample_id, cv_text=cv_text, gold=gold, raw=raw_item))

    return samples, skipped


def load_split(path: str | Path) -> list[Sample]:
    """Read a JSONL split and return list of valid Sample instances."""
    samples, _ = load_split_with_stats(path)
    return samples
