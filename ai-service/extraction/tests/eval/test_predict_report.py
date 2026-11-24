"""Unit tests for eval.predict, eval.variants, and eval.report."""

from __future__ import annotations

from dataclasses import dataclass
import http.server
import json
from pathlib import Path
import threading
from typing import Any
import pytest

from eval.dataset import load_split
from eval.metrics import aggregate, score_sample
from eval.predict import run_predictions
from eval.report import build_report
from eval.variants import VARIANTS


@dataclass
class SyntheticSample:
    id: str
    cv_text: str
    gold: dict[str, Any]
    raw: dict[str, Any]


class MockServerHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass  # Suppress server request logging

    def do_POST(self) -> None:
        content_len = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_len)
        body_str = body_bytes.decode("utf-8")
        self.server.request_bodies.append(body_str)

        try:
            req_data = json.loads(body_str)
        except Exception:
            req_data = {}

        cv_text = req_data.get("cv_text", "")
        if "trigger_413" in cv_text:
            self.send_response(413)
            self.end_headers()
            self.wfile.write(b"Payload Too Large")
            return

        resp = {
            "status": "success",
            "data": {
                "personal_info": {
                    "full_name": "Nguyen Van A",
                    "email": "a@example.com",
                    "phone": "0912345678",
                    "github_url": "github.com/nguyenvana",
                },
                "education": [{"school": "DH Bach Khoa"}],
                "experience": [{"company": "Cong ty FPT", "job_title": "Developer"}],
                "personal_projects": [{"name": "AI App"}],
                "skills": ["Python", "FastAPI"],
                "certificates": ["AWS Certified"],
                "honours": ["First Prize"],
                "languages": [{"language": "Vietnamese", "note": "Native"}],
            },
        }
        resp_bytes = json.dumps(resp).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.end_headers()
        self.wfile.write(resp_bytes)


@pytest.fixture
def mock_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), MockServerHandler)
    server.request_bodies = []
    host, port = server.server_address
    base_url = f"http://{host}:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, base_url
    finally:
        server.shutdown()
        server.server_close()


def test_predict_and_resume(mock_server: Any, tmp_path: Path) -> None:
    server, base_url = mock_server
    run_dir = tmp_path / "run_test"

    samples = [
        SyntheticSample(
            id="sample_01",
            cv_text="Nguyen Van A a@example.com 0912345678 DH Bach Khoa Cong ty FPT",
            gold={},
            raw={},
        ),
        SyntheticSample(
            id="sample_02",
            cv_text="CV too big trigger_413 for error test",
            gold={},
            raw={},
        ),
    ]

    # First run: should execute 2 requests
    records = run_predictions(samples, base_url=base_url, run_dir=run_dir, timeout=10.0)
    assert len(server.request_bodies) == 2
    assert len(records) == 2

    pred_file = run_dir / "predictions.jsonl"
    assert pred_file.exists()

    lines = [json.loads(line) for line in pred_file.read_text(encoding="utf-8").strip().splitlines()]
    assert len(lines) == 2
    assert lines[0]["id"] == "sample_01"
    assert lines[0]["status"] == 200
    assert isinstance(lines[0]["data"], dict)
    assert lines[0]["latency_s"] >= 0.0

    assert lines[1]["id"] == "sample_02"
    assert lines[1]["status"] == 413
    assert lines[1]["data"] is None

    # Resume run: should skip already cached predictions and make 0 new requests
    records_resumed = run_predictions(samples, base_url=base_url, run_dir=run_dir, timeout=10.0)
    assert len(server.request_bodies) == 2
    assert len(records_resumed) == 2


def test_variants() -> None:
    raw_data = {
        "personal_info": {
            "name": "Nguyen Van A",
            "email": "a@example.com",
            "phone_number": "0912345678",
        },
        "skills": "Python, Docker",
    }
    cv_text = "Nguyen Van A a@example.com 0912345678 Python Docker"

    # Variant A returns identical data
    out_a = VARIANTS["A"](raw_data, cv_text)
    assert out_a == raw_data

    # Variant B returns postprocessed profile
    out_b = VARIANTS["B"](raw_data, cv_text)
    assert isinstance(out_b, dict)
    assert out_b["personal_info"]["full_name"] == "Nguyen Van A"
    assert out_b["personal_info"]["phone"] == "0912345678"
    assert "Python" in out_b["skills"]
    assert "Docker" in out_b["skills"]

    # Non-dict returns itself
    assert VARIANTS["B"](None, cv_text) is None


def test_build_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # 1. Create a synthetic split file
    split_file = tmp_path / "val_synthetic.jsonl"
    sample1_raw = {
        "instruction": "extract",
        "input": "Nguyen Van A a@example.com 0912345678 DH Bach Khoa Cong ty FPT Developer Python",
        "output": json.dumps({
            "personal_info": {
                "full_name": "Nguyen Van A",
                "email": "a@example.com",
                "phone": "0912345678",
                "github_url": None,
            },
            "education": [{"school": "DH Bach Khoa"}],
            "experience": [{"company": "Cong ty FPT", "job_title": "Developer"}],
            "skills": ["Python"],
        }),
    }
    sample2_raw = {
        "instruction": "extract",
        "input": "Tran Van B b@example.com",
        "output": json.dumps({
            "personal_info": {
                "full_name": "Tran Van B",
                "email": "b@example.com",
                "phone": None,
                "github_url": None,
            },
        }),
    }
    with split_file.open("w", encoding="utf-8") as f:
        f.write(json.dumps(sample1_raw) + "\n")
        f.write(json.dumps(sample2_raw) + "\n")

    # Load split to obtain deterministic IDs
    samples = load_split(split_file)
    assert len(samples) == 2

    # 2. Write predictions.jsonl in run_dir
    run_dir = tmp_path / "run_report"
    run_dir.mkdir(parents=True, exist_ok=True)
    pred_file = run_dir / "predictions.jsonl"

    pred_records = [
        {
            "id": samples[0].id,
            "status": 200,
            "data": {
                "personal_info": {
                    "full_name": "Nguyen Van A",
                    "email": "a@example.com",
                    "phone": "0912345678",
                    "github_url": None,
                },
                "education": [{"school": "DH Bach Khoa"}],
                "experience": [{"company": "Cong ty FPT", "job_title": "Developer"}],
                "skills": ["Python"],
            },
            "latency_s": 1.25,
        },
        {
            "id": samples[1].id,
            "status": 413,
            "data": None,
            "latency_s": 0.05,
        },
    ]
    with pred_file.open("w", encoding="utf-8") as f:
        for r in pred_records:
            f.write(json.dumps(r) + "\n")

    # 3. Build report
    report = build_report(run_dir=run_dir, split_paths=[split_file], variants=("A", "B"))

    assert "splits" in report
    assert "val_synthetic" in report["splits"]
    val_split = report["splits"]["val_synthetic"]
    assert "A" in val_split and "B" in val_split
    assert val_split["A"]["n"] == 2
    assert val_split["A"]["missing"] == 0

    # 4. Check written artifacts
    assert (run_dir / "scores.jsonl").exists()
    assert (run_dir / "report.json").exists()
    assert (run_dir / "report.md").exists()

    md_content = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "| Metric | val_synthetic / A | val_synthetic / B |" in md_content
    assert "Schema validity rate" in md_content
    assert "Hallucination rate" in md_content
    assert "experience.company (F1)" in md_content
    assert "personal_info.full_name (Acc)" in md_content
    assert "Latency mean (s)" in md_content

    # Check console output
    captured = capsys.readouterr()
    assert "# Evaluation Report" in captured.out
