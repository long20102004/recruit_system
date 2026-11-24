"""Integration tests for the end-to-end postprocessing pipeline."""

from __future__ import annotations

import json
import logging
import time

from app.postprocess.pipeline import PostprocessStats, postprocess

SYNTHETIC_CV_TEXT = """
HỌ VÀ TÊN: Nguyễn Văn A
Email: nguyen.van.a@example.com
Số điện thoại: 0987654321

HỌC VẤN
Trường Đại học Bách Khoa Hà Nội
Chuyên ngành: Công nghệ thông tin (2018 - 2022)

KINH NGHIỆM LÀM VIỆC
Công ty Cổ phần Công nghệ ABC
Vị trí: Backend Developer (2022 - 2024)
- Thiết kế và phát triển RESTful APIs sử dụng Spring Boot và Java.
- Tối ưu hóa cơ sở dữ liệu PostgreSQL.

KỸ NĂNG CHUYÊN MÔN
Java, Spring Boot, PostgreSQL, Docker, Git
"""

SYNTHETIC_HALLUCINATED_OUTPUT = {
    "personal_info": {
        "name": "Nguyễn Văn A",
        "email": "nguyen.van.a@example.com",
        "phone": "0987654321",
        "github_url": "https://github.com/yourusername",
    },
    "objective": "Trở thành Senior Software Engineer dẫn dắt đội ngũ kỹ thuật trong 3 năm tới",
    "education": [
        {
            "school": "Trường Đại học Bách Khoa Hà Nội",
            "major": "Công nghệ thông tin",
            "start_year": "2018",
            "end_year": "2022",
        }
    ],
    "experience": [
        {
            "company": "Công ty Cổ phần Công nghệ ABC",
            "job_title": "Backend Developer",
            "start_date": "2022",
            "end_date": "2024",
            "description": [
                "Thiết kế và phát triển RESTful APIs sử dụng Spring Boot và Java."
            ],
        }
    ],
    "personal_projects": [],
    "skills": ["Backend: Spring Boot", "Java", "Docker"],
    "honors": ["Nhân viên xuất sắc năm 2023"],
    "languages": [{"language": "English", "note": "TOEFL 90"}],
}


def test_postprocess_hallucination_example():
    """(1) postprocess on hallucination example cleans fake fields and normalises keys."""
    profile, stats = postprocess(SYNTHETIC_HALLUCINATED_OUTPUT, SYNTHETIC_CV_TEXT)

    assert profile["personal_info"]["github_url"] is None
    assert profile["objective"] is None
    assert profile["languages"] == []
    assert "honours" in profile
    assert isinstance(profile["honours"], list)
    assert "Spring Boot" in profile["skills"]

    stats_dict = stats.as_dict()
    assert "contacts_nulled" in stats_dict
    assert stats_dict["contacts_nulled"] >= 1
    assert all(value > 0 for value in stats_dict.values())


def test_extract_cv_route_postprocessed(client, fake_engine, caplog):
    """(2) extract-cv route executes postprocessing, logs counts without leaking CV values."""
    caplog.set_level(logging.INFO)
    fake_engine.output = json.dumps(SYNTHETIC_HALLUCINATED_OUTPUT)

    response = client.post("/api/v1/extract-cv", json={"cv_text": SYNTHETIC_CV_TEXT})
    assert response.status_code == 200

    data = response.json()["data"]
    assert data["personal_info"]["github_url"] is None
    assert data["objective"] is None
    assert data["languages"] == []
    assert isinstance(data["honours"], list)
    assert "Spring Boot" in data["skills"]

    assert "postprocess" in caplog.text
    assert "nguyen.van.a@example.com" not in caplog.text
    assert "0987654321" not in caplog.text


def test_postprocess_disabled_flag(client, fake_engine, monkeypatch):
    """(3) Disabling post-processing via config returns raw output untouched."""
    monkeypatch.setattr("app.core.config.POSTPROCESS_ENABLED", False)
    fake_engine.output = json.dumps(SYNTHETIC_HALLUCINATED_OUTPUT)

    response = client.post("/api/v1/extract-cv", json={"cv_text": SYNTHETIC_CV_TEXT})
    assert response.status_code == 200

    data = response.json()["data"]
    assert data == json.loads(fake_engine.output)


def test_postprocess_exception_fallback(client, fake_engine, monkeypatch):
    """(4) Postprocessing runtime error falls back to returning raw un-postprocessed data with 200."""
    def _raise_error(*args, **kwargs):
        raise RuntimeError("Postprocess failure simulation")

    monkeypatch.setattr("app.api.routes.postprocess", _raise_error)
    fake_engine.output = json.dumps(SYNTHETIC_HALLUCINATED_OUTPUT)

    response = client.post("/api/v1/extract-cv", json={"cv_text": SYNTHETIC_CV_TEXT})
    assert response.status_code == 200

    data = response.json()["data"]
    assert data == json.loads(fake_engine.output)


def test_postprocess_performance():
    """(5) Average postprocessing duration over 20 runs is < 0.1s on a ~3000 character CV."""
    base_chunk = (
        "HỌ VÀ TÊN: Nguyễn Văn A\n"
        "Email: nguyen.van.a@example.com\n"
        "Điện thoại: 0987654321\n"
        "HỌC VẤN: Trường Đại học Bách Khoa Hà Nội, Công nghệ thông tin (2018 - 2022), GPA 3.6.\n"
        "KINH NGHIỆM: Công ty Cổ phần Công nghệ ABC - Backend Developer (2022 - 2024).\n"
        "DỰ ÁN: Hệ thống thương mại điện tử với công nghệ Spring Boot, Redis, PostgreSQL.\n"
        "KỸ NĂNG: Java, Spring Boot, PostgreSQL, Docker, Kubernetes, Git, CI/CD, Microservices.\n"
        "CHỨNG CHỈ: AWS Certified Developer Associate.\n"
        "GIẢI THƯỞNG: Nhân viên xuất sắc năm 2023.\n"
        "NGOẠI NGỮ: Tiếng Anh giao tiếp tốt.\n"
    )
    long_cv = (base_chunk * ((3000 // len(base_chunk)) + 1))[:3000]
    assert 2900 <= len(long_cv) <= 3100

    durations: list[float] = []
    for _ in range(20):
        start = time.perf_counter()
        postprocess(SYNTHETIC_HALLUCINATED_OUTPUT, long_cv)
        durations.append(time.perf_counter() - start)

    avg_duration = sum(durations) / len(durations)
    assert avg_duration < 0.1, f"Average duration {avg_duration:.4f}s exceeded 0.1s threshold"
