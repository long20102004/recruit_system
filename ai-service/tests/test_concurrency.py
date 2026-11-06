"""T015 — Không có race condition: lock bảo vệ inference tuần tự.

(a) Gọi ``generate_cv`` từ 5 thread: fake LLM sleep 0.05s và đếm số luồng
đang active (lock riêng) — engine giả serial nên ``max_active == 1`` và
mỗi kết quả chứa đúng marker ``CV-<i>`` của prompt tương ứng.
(b) Khi ``_lock`` đã bị giữ, request POST qua API trả 503 sau
``QUEUE_WAIT_SECONDS`` với detail đúng contract.

Chỉ dùng CV tổng hợp (synthetic), không có dữ liệu CV thật.
"""

import re
import threading
import time

import pytest

from app.core import config
from app.services import model_loader
from app.services.generator import _lock, generate_cv

SYNTHETIC_CV = "Nguyễn Văn A\nKỹ năng: Python, FastAPI\nKinh nghiệm: 2 năm"


class OverlapTrackingFakeLlm:
    """Fake Llama (giống FakeLlm): tokenize giả + ``__call__`` sleep.

    Đếm số luồng đang nằm trong ``__call__`` bằng lock riêng để phát hiện
    hai luồng chạy inference chồng lấn; ghi nhận ``max_active``.
    Kết quả trả về chứa marker lấy từ prompt (``CV-<i>`` trong cv_text).
    """

    def __init__(self, sleep_seconds: float = 0.05, token_count: int = 100):
        self.sleep_seconds = sleep_seconds
        self.token_count = token_count
        self.calls = 0
        self.max_active = 0
        self._active = 0
        self._counter_lock = threading.Lock()

    def tokenize(self, text: bytes, add_bos=True, special=False):
        return [0] * self.token_count

    def __call__(self, prompt, **kwargs):
        with self._counter_lock:
            self.calls += 1
            self._active += 1
            self.max_active = max(self.max_active, self._active)
        try:
            time.sleep(self.sleep_seconds)
        finally:
            with self._counter_lock:
                self._active -= 1

        match = re.search(r"CV-\d+", prompt)
        marker = match.group(0) if match else "CV-unknown"
        return {
            "choices": [
                {"text": '{"personal_info": {}, "source": "%s"}' % marker}
            ],
            "usage": {
                "prompt_tokens": self.token_count,
                "completion_tokens": 10,
            },
        }


@pytest.fixture()
def overlap_fake_llm(fake_engine, monkeypatch):
    """Thay engine giả bằng OverlapTrackingFakeLlm (state đã set)."""
    fake = OverlapTrackingFakeLlm()
    monkeypatch.setattr(model_loader.state, "llm", fake)
    return fake


def test_generate_cv_serialized_across_5_threads(overlap_fake_llm):
    """5 thread gọi generate_cv đồng thời: không có inference chồng lấn."""
    cvs = ["REF: CV-%d\n%s" % (i, SYNTHETIC_CV) for i in range(5)]
    results: list = [None] * len(cvs)
    errors: list = []
    barrier = threading.Barrier(len(cvs))

    def worker(i: int):
        try:
            barrier.wait(timeout=5)
            results[i] = generate_cv(cvs[i])
        except BaseException as e:  # noqa: BLE001 - gom mọi lỗi về main thread
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(cvs))]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
    finally:
        barrier.abort()

    assert not errors, errors
    assert overlap_fake_llm.calls == len(cvs)
    # Engine giả serial (chỉ 1 llm) nên không bao giờ 2 luồng chạy __call__
    assert overlap_fake_llm.max_active == 1
    for i, raw_output in enumerate(results):
        assert raw_output is not None
        assert "CV-%d" % i in raw_output  # đúng marker của prompt tương ứng


def test_extract_cv_503_when_lock_held(client, fake_engine, monkeypatch):
    """Lock bị giữ > QUEUE_WAIT_SECONDS -> 503 'Service đang bận'."""
    monkeypatch.setattr(config, "QUEUE_WAIT_SECONDS", 0.05)

    assert _lock.acquire(blocking=False)
    try:
        resp = client.post("/api/v1/extract-cv", json={"cv_text": SYNTHETIC_CV})
    finally:
        _lock.release()

    assert resp.status_code == 503
    assert resp.json()["detail"] == "Service đang bận, vui lòng thử lại sau"
