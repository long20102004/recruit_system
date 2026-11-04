"""T014 — Ngân sách token của prompt: dưới hạn → 200, vượt hạn → 413.

Chỉ dùng CV tổng hợp (synthetic); engine giả ``fake_engine`` đếm token
cố định nên không cần dữ liệu CV thật.
"""

import pytest

CONTEXT_TOKENS = 8192
MAX_NEW_TOKENS = 1500

# CV tổng hợp, nội dung không ảnh hưởng vì tokenize được fake.
SYNTHETIC_CV = "Nguyễn Văn A\nKỹ năng: Python, FastAPI\nKinh nghiệm: 2 năm"


@pytest.fixture()
def budget(monkeypatch, fake_engine):
    """Ép ``MAX_NEW_TOKENS=1500`` và trả về engine giả đã cài vào state."""
    monkeypatch.setattr("app.services.generator.MAX_NEW_TOKENS", MAX_NEW_TOKENS)
    return fake_engine


def test_prompt_du_han_tra_ve_200_va_chay_generation(client, budget):
    budget.token_count = CONTEXT_TOKENS - MAX_NEW_TOKENS  # 6692 == max_prompt

    resp = client.post("/api/v1/extract-cv", json={"cv_text": SYNTHETIC_CV})

    assert resp.status_code == 200
    assert resp.json()["data"] == {"personal_info": {}}
    assert budget.calls == 1


def test_prompt_vuot_han_tra_ve_413_khong_generation(client, budget):
    budget.token_count = CONTEXT_TOKENS - MAX_NEW_TOKENS + 1  # 6693 > max_prompt

    resp = client.post("/api/v1/extract-cv", json={"cv_text": SYNTHETIC_CV})

    assert resp.status_code == 413
    detail = resp.json()["detail"]
    assert "6693" in detail  # prompt tokens thực tế
    assert "6692" in detail  # max_prompt = context - MAX_NEW_TOKENS
    assert budget.calls == 0
