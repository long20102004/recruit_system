"""Prompt selection and configuration without loading a real model."""

import os
import subprocess
import sys

import pytest

from app.core import config
from app.services import generator, prompt, prompt_v2


def config_process(**env_vars):
    env = os.environ.copy()
    env.pop("PROMPT_VERSION", None)
    env.pop("MAX_NEW_TOKENS", None)
    env.update(env_vars)
    return subprocess.run(
        [sys.executable, "-c", "from app.core import config; print(config.PROMPT_VERSION, config.MAX_NEW_TOKENS)"],
        env=env, capture_output=True, text=True,
    )


@pytest.mark.parametrize("env_vars, expected", [
    ({}, "v4 2048"),
    ({"PROMPT_VERSION": " V2 "}, "v2 2048"),
    ({"PROMPT_VERSION": "v2", "MAX_NEW_TOKENS": "123"}, "v2 123"),
    ({"PROMPT_VERSION": "v1", "MAX_NEW_TOKENS": "456"}, "v1 456"),
])
def test_config_defaults_and_overrides(env_vars, expected):
    result = config_process(**env_vars)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


def test_invalid_prompt_version_fails_import():
    result = config_process(PROMPT_VERSION="invalid")
    assert result.returncode != 0
    assert "ValueError: PROMPT_VERSION" in result.stderr


def test_prompt_selection(monkeypatch):
    cv = "Synthetic CV: Python"
    monkeypatch.setattr(config, "PROMPT_VERSION", "v1")
    assert generator.build_prompt(cv) == prompt.build_prompt_gguf(cv)
    monkeypatch.setattr(config, "PROMPT_VERSION", "v2")
    result = generator.build_prompt(cv)
    assert result == prompt_v2.render_prompt(cv)
    assert result.endswith("<think>\n\n</think>\n\n")
    assert not result.endswith("{")


def test_serving_uses_v2_and_runtime_budget(monkeypatch, fake_engine, client):
    monkeypatch.setattr(config, "PROMPT_VERSION", "v2")
    monkeypatch.setattr(config, "MAX_NEW_TOKENS", 321)
    captured = {}

    def generate(self, prompt, **kwargs):
        captured.update(prompt=prompt, **kwargs)
        return {"choices": [{"text": '{"personal_info": {"full_name": "Synthetic Name"}}'}]}

    monkeypatch.setattr(type(fake_engine), "__call__", generate)
    response = client.post("/api/v1/extract-cv", json={"cv_text": "Synthetic CV"})
    assert response.status_code == 200
    assert captured["prompt"] == prompt_v2.render_prompt("Synthetic CV")
    assert captured["max_tokens"] == 321
    assert client.get("/health").json()["prompt_version"] == "v2"


def test_v2_without_v2_model_refuses_v1_adapter(monkeypatch):
    from app.services import model_loader

    monkeypatch.setattr(config, "PROMPT_VERSION", "v2")
    monkeypatch.setattr(model_loader, "resolve_gguf_path", lambda p: (None, "Không tìm thấy file GGUF"))
    with pytest.raises(RuntimeError, match="PROMPT_VERSION=v2"):
        model_loader.load_model()


def test_default_model_file_follows_prompt_version():
    for version, name in (("v1", "model.gguf"), ("v2", "model-v2-q4_k_m.gguf")):
        result = subprocess.run(
            [sys.executable, "-c", "from app.core import config; print(config.GGUF_MODEL_PATH)"],
            env={**{k: v for k, v in os.environ.items() if k not in ("GGUF_MODEL_PATH",)}, "PROMPT_VERSION": version},
            capture_output=True, text=True,
        )
        assert result.stdout.strip().endswith(name), result.stderr



def test_v4_uses_prompt_v3_and_its_own_model(monkeypatch):
    """Feature 013: v4 = prompt v3 + model-v4 GGUF."""
    from app.core import config
    from app.services import generator, prompt_v3

    monkeypatch.setattr(config, "PROMPT_VERSION", "v4")
    assert generator.build_prompt("Synthetic CV") == prompt_v3.render_prompt("Synthetic CV")
    assert config.DEFAULT_GGUF["v4"].endswith("model-v4-q4_k_m.gguf")


def test_v5_uses_prompt_v3_and_its_own_model(monkeypatch):
    """Feature 014: v5 = prompt v3 + model-v5 GGUF."""
    from app.core import config
    from app.services import generator, prompt_v3

    monkeypatch.setattr(config, "PROMPT_VERSION", "v5")
    assert generator.build_prompt("Synthetic CV") == prompt_v3.render_prompt("Synthetic CV")
    assert config.DEFAULT_GGUF["v5"].endswith("model-v5-q4_k_m.gguf")
