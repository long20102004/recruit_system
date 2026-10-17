"""Chạy nhanh end-to-end: train fast + chấm 1 câu mẫu."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    print("=== HireLens AI demo (Spring Boot intern/fresher) ===\n")
    subprocess.check_call(
        [sys.executable, "-m", "src.train_calibration", "--mode", "fast"],
        cwd=ROOT,
    )
    sample = (
        "Spring Boot dựa trên Spring, có auto-configuration và starter, "
        "thường dùng để viết REST API, chạy bằng jar với Tomcat nhúng."
    )
    print("\n=== Chấm câu mẫu sb-01 ===\n")
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "src.predict_answer",
            "--mode",
            "fast",
            "--question-id",
            "sb-01",
            "--answer",
            sample,
        ],
        cwd=ROOT,
    )
    calib = json.loads((ROOT / "output" / "calibration_fast.json").read_text(encoding="utf-8"))
    print("\nTóm tắt metrics test:", calib["metrics"]["ridge_test"])


if __name__ == "__main__":
    main()
