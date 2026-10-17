"""Đọc questions / answers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = ROOT / "output"


def load_questions(path: Path | None = None) -> dict[str, Any]:
    path = path or DATA / "questions.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def questions_by_id(bundle: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    bundle = bundle or load_questions()
    return {q["id"]: q for q in bundle["questions"]}


def load_answers(path: Path | None = None) -> pd.DataFrame:
    path = path or DATA / "answers.csv"
    return pd.read_csv(path)
