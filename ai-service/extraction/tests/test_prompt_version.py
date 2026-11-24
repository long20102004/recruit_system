"""Prompt selection and configuration without loading a real model."""

import os
import subprocess
import sys

import pytest

from app.core import config
from app.services import generator, prompt_v3


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
    ({"PROMPT_VERSION": " V4 "}, "v4 2048"),
    ({"PROMPT_VERSION": "v4", "MAX_NEW_TOKENS": "123"}, "v4 123"),
])
def test_config_defaults_and_overrides(env_vars, expected):
    result = config_process(**env_vars)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


@pytest.mark.parametrize("version", ["v1", "v2", "v3", "v5", "invalid"])
def test_removed_or_invalid_prompt_version_fails_import(version):
    result = config_process(PROMPT_VERSION=version)
    assert result.returncode != 0
    assert "ValueError: PROMPT_VERSION" in result.stderr


def test_prompt_selection(monkeypatch):
    cv = "Synthetic CV: Python"
    monkeypatch.setattr(config, "PROMPT_VERSION", "v4")
    result = generator.build_prompt(cv)
    assert result == prompt_v3.render_prompt(cv)
    assert result.endswith(prompt_v3.ASSISTANT_PREFIX)
    assert not result.endswith("{")


def test_serving_uses_v4_and_runtime_budget(monkeypatch, fake_engine, client):
    monkeypatch.setattr(config, "PROMPT_VERSION", "v4")
    monkeypatch.setattr(config, "MAX_NEW_TOKENS", 321)
    captured = {}

    def generate(self, prompt, **kwargs):
        captured.update(prompt=prompt, **kwargs)
        return {"choices": [{"text": '{"personal_info": {"full_name": "Synthetic Name"}}'}]}

    monkeypatch.setattr(type(fake_engine), "__call__", generate)
    response = client.post("/api/v1/extract-cv", json={"cv_text": "Synthetic CV"})
    assert response.status_code == 200
    assert captured["prompt"] == prompt_v3.render_prompt("Synthetic CV")
    assert captured["max_tokens"] == 321
    assert client.get("/health").json()["prompt_version"] == "v4"


def test_render_target_matches_prompt_v3_format():
    profile = {
        "skills": ["Python"],
        "objective": None,
        "personal_info": {"full_name": "Synthetic Name"},
        "ignored": "x",
    }
    assert prompt_v3.render_target(profile) == (
        '{"personal_info":{"full_name":"Synthetic Name"},"objective":null,"skills":["Python"]}'
        + prompt_v3.END_OF_TURN
    )


def test_default_model_file_and_adapter_are_v4():
    env = {k: v for k, v in os.environ.items() if k not in ("GGUF_MODEL_PATH", "LORA_PATH")}
    env["PROMPT_VERSION"] = "v4"
    result = subprocess.run(
        [sys.executable, "-c",
         "from app.core import config; print(config.GGUF_MODEL_PATH); print(config.LORA_PATH)"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["./merged_model/model-v4-q4_k_m.gguf", "./checkpoint-v4"]


def test_v4_uses_prompt_v3_and_its_own_model(monkeypatch):
    """Feature 013: v4 = prompt v3 + model-v4 GGUF."""
    monkeypatch.setattr(config, "PROMPT_VERSION", "v4")
    assert generator.build_prompt("Synthetic CV") == prompt_v3.render_prompt("Synthetic CV")
    assert config.DEFAULT_GGUF["v4"].endswith("model-v4-q4_k_m.gguf")
    assert config.DEFAULT_LORA["v4"] == "./checkpoint-v4"
