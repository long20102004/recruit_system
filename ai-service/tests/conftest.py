"""Shared test fixtures for the AI service.

Không import torch/llama_cpp/transformers: ``load_model`` được no-op và
engine giả được cài trực tiếp vào ``app.services.model_loader.state``.
"""

import pytest
from fastapi.testclient import TestClient

from app.services import model_loader


class FakeLlm:
    """Thay thế llama_cpp.Llama: tokenize giả (độ dài cố định) và __call__
    trả về JSON text cố định, không dùng dữ liệu CV thật."""

    def __init__(self, output='{"personal_info": {}}', token_count=100):
        self.output = output
        self.token_count = token_count
        self.calls = 0

    def tokenize(self, text: bytes, add_bos=True, special=False):
        return [0] * self.token_count

    def __call__(self, prompt, **kwargs):
        self.calls += 1
        return {
            "choices": [{"text": self.output}],
            "usage": {
                "prompt_tokens": self.token_count,
                "completion_tokens": 10,
            },
        }


@pytest.fixture(autouse=True)
def no_model_load(monkeypatch):
    """Chặn load_model thật khi FastAPI startup chạy trong TestClient."""
    monkeypatch.setattr("app.main.load_model", lambda: None)
    # Tests opt in to KG enrichment by setting app.kb.store.kb_state["kb"] themselves.
    monkeypatch.setattr("app.main.load_kb", lambda *a, **k: None)
    from app.kb.store import kb_state

    kb_state["kb"] = None


@pytest.fixture()
def fake_engine():
    fake = FakeLlm()
    model_loader.state.engine = "llama_cpp"
    model_loader.state.llm = fake
    model_loader.state.gguf_path_used = "/models/fake.gguf"
    model_loader.state.context_tokens = 8192
    model_loader.state.fallback_reason = None
    yield fake
    # Reset từng thuộc tính về None để tests độc lập nhau
    model_loader.state.engine = None
    model_loader.state.llm = None
    model_loader.state.tokenizer = None
    model_loader.state.model = None
    model_loader.state.gguf_path_used = None
    model_loader.state.context_tokens = None
    model_loader.state.fallback_reason = None


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c
