"""Tests cho việc dò file GGUF và contract của GET /health.

Chỉ dùng tmp_path và dữ liệu tổng hợp (synthetic), không đụng model thật.
"""

from app.services import model_loader
from app.services.model_loader import resolve_gguf_path


# ---------------------------------------------------------------------------
# resolve_gguf_path
# ---------------------------------------------------------------------------

def test_configured_file_exists_returns_it(tmp_path):
    configured = tmp_path / "my-model.gguf"
    configured.write_bytes(b"GGUF")

    path, reason = resolve_gguf_path(str(configured))

    assert path == str(configured)
    assert reason is None


def test_single_gguf_in_dir_is_used_and_gitkeep_ignored(tmp_path):
    expected = tmp_path / "model.gguf"
    expected.write_bytes(b"GGUF")
    (tmp_path / ".gitkeep").write_text("")

    # configured không tồn tại -> fallback sang quét thư mục cha
    path, reason = resolve_gguf_path(str(tmp_path / "configured-name.gguf"))

    assert path == str(expected)
    assert reason is None


def test_no_gguf_in_dir_returns_reason(tmp_path):
    (tmp_path / ".gitkeep").write_text("")

    path, reason = resolve_gguf_path(str(tmp_path / "missing.gguf"))

    assert path is None
    assert isinstance(reason, str) and reason


def test_multiple_gguf_in_dir_returns_reason_mentioning_env(tmp_path):
    (tmp_path / "a.gguf").write_bytes(b"GGUF")
    (tmp_path / "b.gguf").write_bytes(b"GGUF")

    path, reason = resolve_gguf_path(str(tmp_path / "missing.gguf"))

    assert path is None
    assert "GGUF_MODEL_PATH" in reason


def test_missing_parent_dir_returns_reason(tmp_path):
    missing_dir = tmp_path / "does-not-exist"

    path, reason = resolve_gguf_path(str(missing_dir / "model.gguf"))

    assert path is None
    assert isinstance(reason, str) and reason


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def test_health_has_context_tokens_without_fallback_reason(fake_engine, client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["engine"] == "llama_cpp"
    assert body["context_tokens"] == 8192
    assert "fallback_reason" not in body


def test_health_exposes_fallback_reason_when_set(fake_engine, client):
    model_loader.state.fallback_reason = "x"

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["context_tokens"] == 8192
    assert body["fallback_reason"] == "x"
