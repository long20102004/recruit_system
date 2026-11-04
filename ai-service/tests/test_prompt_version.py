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
    ({}, "v1 1500"),
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
        return {"choices": [{"text": '{"personal_info": {}}'}]}

    monkeypatch.setattr(type(fake_engine), "__call__", generate)
    response = client.post("/api/v1/extract-cv", json={"cv_text": "Synthetic CV"})
    assert response.status_code == 200
    assert captured["prompt"] == prompt_v2.render_prompt("Synthetic CV")
    assert captured["max_tokens"] == 321
    assert client.get("/health").json()["prompt_version"] == "v2"
