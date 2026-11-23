"""Tests về bảo mật dữ liệu CV (privacy) cho POST /api/v1/extract-cv.

Chỉ dùng dữ liệu CV tổng hợp (synthetic). Đảm bảo:
- 200 trả JSON extracted + X-Request-ID 12 ký tự;
- PII từ CV/raw output KHÔNG lọt vào logs (mặc định);
- 500 không lộ exception text, chỉ có request_id;
- 400 cho cv_text rỗng/whitespace;
- 503 khi model chưa load;
- Bật LOG_CV_CONTENT=True thì raw output (chứa PII) được log rõ ràng.
"""

import logging

import pytest

SYNTHETIC_EMAIL = "zz.synthetic.001@example.test"
SYNTHETIC_PHONE = "0900000001"

SYNTHETIC_CV = f"""Nguyen Van Test
Email: {SYNTHETIC_EMAIL}
Phone: {SYNTHETIC_PHONE}
Học vấn: Trường THPT Synthetic, 2015-2018
Kỹ năng: Python
"""

FAKE_OUTPUT = (
    "{{"
    "\"personal_info\": {{"
    "\"full_name\": \"Nguyen Van Test\","
    "\"email\": \"{email}\","
    "\"phone\": \"{phone}\","
    "\"github_url\": null"
    "}},"
    "\"objective\": null,"
    "\"education\": [],"
    "\"experience\": [],"
    "\"personal_projects\": [],"
    "\"skills\": [],"
    "\"certificates\": [],"
    "\"honours\": [],"
    "\"languages\": []"
    "}}"
).format(email=SYNTHETIC_EMAIL, phone=SYNTHETIC_PHONE)


def test_extract_ok_no_pii_in_logs(client, fake_engine, caplog):
    """(a) Trích xuất thành công; PII không xuất hiện trong logs."""
    fake_engine.output = FAKE_OUTPUT

    with caplog.at_level(logging.DEBUG):
        resp = client.post(
            "/api/v1/extract-cv", json={"cv_text": SYNTHETIC_CV}
        )

    assert resp.status_code == 200
    assert len(resp.headers["X-Request-ID"]) == 12

    data = resp.json()["data"]
    assert data["personal_info"]["email"] == SYNTHETIC_EMAIL
    assert data["personal_info"]["phone"] == SYNTHETIC_PHONE

    assert SYNTHETIC_EMAIL not in caplog.text
    assert SYNTHETIC_PHONE not in caplog.text


def test_internal_error_no_exception_leak(client, fake_engine, caplog, monkeypatch):
    """(b) Lỗi bên trong -> 500 có request_id, không lộ exception message."""

    def broken_generate_cv(cv_text: str) -> str:
        raise RuntimeError(f"boom: {SYNTHETIC_EMAIL}")

    monkeypatch.setattr("app.api.routes.generate_cv_result", broken_generate_cv)

    with caplog.at_level(logging.DEBUG):
        resp = client.post(
            "/api/v1/extract-cv", json={"cv_text": SYNTHETIC_CV}
        )

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "request_id=" in detail
    assert SYNTHETIC_EMAIL not in detail

    assert SYNTHETIC_EMAIL not in caplog.text


def test_blank_cv_text_returns_400(client, fake_engine):
    """(c) cv_text chỉ whitespace -> 400."""
    resp = client.post("/api/v1/extract-cv", json={"cv_text": "   "})

    assert resp.status_code == 400
    assert resp.json()["detail"] == "cv_text không được rỗng"


def test_model_not_loaded_returns_503(client):
    """(d) Không có engine -> 503."""
    resp = client.post(
        "/api/v1/extract-cv", json={"cv_text": SYNTHETIC_CV}
    )

    assert resp.status_code == 503
    assert resp.json()["detail"] == "Model chưa được load"


def test_log_cv_content_enabled_logs_raw_output(client, fake_engine, caplog, monkeypatch):
    """(e) LOG_CV_CONTENT=True -> raw output (chứa PII synthesis) được log."""
    fake_engine.output = FAKE_OUTPUT
    monkeypatch.setattr("app.core.config.LOG_CV_CONTENT", True)

    with caplog.at_level(logging.DEBUG):
        resp = client.post(
            "/api/v1/extract-cv", json={"cv_text": SYNTHETIC_CV}
        )

    assert resp.status_code == 200
    assert SYNTHETIC_EMAIL in caplog.text
    assert SYNTHETIC_PHONE in caplog.text
