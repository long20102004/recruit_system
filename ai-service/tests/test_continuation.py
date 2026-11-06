import json
import runpy

import pytest

from app.core import config
from app.services import generator
from app.services.continuation import TOP_KEYS, merge_outputs, plan_continuation
from app.services.model_loader import state


@pytest.mark.parametrize("value,expected", [(None, True), ("false", False), ("true", True)])
def test_continuation_environment_default(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("CONTINUATION_ENABLED", raising=False)
    else:
        monkeypatch.setenv("CONTINUATION_ENABLED", value)
    assert runpy.run_path(config.__file__)["CONTINUATION_ENABLED"] is expected


def profile_through(key):
    return {name: [] for name in TOP_KEYS[:TOP_KEYS.index(key) + 1]}


def test_complete_profile_needs_no_continuation():
    text = json.dumps(dict.fromkeys(TOP_KEYS))
    assert plan_continuation(text, None) is None


def test_missing_tail_after_projects():
    data = profile_through("personal_projects")
    prefix, key = plan_continuation(json.dumps(data), None)
    assert key == "skills"
    assert json.loads(prefix + "}") == data


def test_long_string_drops_unfinished_project():
    data = profile_through("experience")
    project = {"name": 'Synthetic "Project"', "description": ["Complete bullet"]}
    raw = json.dumps(data)[:-1] + ',"personal_projects":[' + json.dumps(project)
    raw += ',{"name":"Unfinished","description":["a never ending description'
    prefix, key = plan_continuation(raw, "long_string")
    assert key == "skills"
    assert json.loads(prefix + "}")["personal_projects"] == [project]


def test_repeated_description_preserves_first_occurrence():
    raw = json.dumps(profile_through("education"))[:-1]
    raw += ',"experience":[{"company":"Synthetic","description":['
    raw += ','.join([json.dumps("Built a synthetic feature")] * 3)
    prefix, key = plan_continuation(raw, "repeated_value")
    assert key == "personal_projects"
    assert json.loads(prefix + "}")["experience"] == [
        {"company": "Synthetic", "description": ["Built a synthetic feature"]},
    ]


@pytest.mark.parametrize("raw", ["garbage", "{not json", "[]", '{"unknown": []}'])
def test_garbage_has_no_plan(raw):
    assert plan_continuation(raw, None) is None


def test_max_tokens_and_unclosed_json_keep_complete_items():
    raw = '{"experience":[{"company":"Complete"},{"company":"incomplete'
    for reason in ("max_tokens", None):
        prefix, key = plan_continuation(raw, reason)
        assert key == "personal_projects"
        assert json.loads(prefix + "}") == {"experience": [{"company": "Complete"}]}


def test_complete_scalar_without_outer_closing_brace():
    prefix, key = plan_continuation('{"objective":null', "max_tokens")
    assert key == "education"
    assert json.loads(prefix + "}") == {"objective": None}


def test_repeated_value_only_removes_trailing_duplicates():
    raw = '{"experience":[{"description":["one","one","two","two"]}]}'
    prefix, key = plan_continuation(raw, "repeated_value")
    assert key == "personal_projects"
    assert json.loads(prefix + "}")["experience"][0]["description"] == ["one", "one", "two"]


def test_merge_outputs_only_fills_missing_or_empty():
    first = {"skills": ["Python"], "objective": "", "education": [],
             "personal_info": None, "count": 0, "flag": False, "mapping": {}}
    second = {"skills": ["Java"], "objective": "Synthetic", "education": ["School"],
              "personal_info": {"full_name": "Synthetic"}, "languages": ["English"],
              "count": 2, "flag": True, "mapping": {"x": 1}}
    merged = merge_outputs(first, second)
    assert merged == {**second, "skills": ["Python"], "count": 0, "flag": False, "mapping": {}}
    assert first["objective"] == ""


@pytest.fixture
def tail_engine(fake_engine, monkeypatch):
    monkeypatch.setattr(config, "CONTINUATION_ENABLED", True)
    monkeypatch.setattr(config, "PROMPT_VERSION", "v3")
    fake_engine.outputs = [json.dumps(profile_through("personal_projects")),
                           '["Python"],"certificates":[],"honours":[],"languages":[]}']
    return fake_engine


def test_generate_continues_once(tail_engine):
    result = generator.generate_cv_result("Synthetic CV with Python")
    assert json.loads(result.text)["skills"] == ["Python"]
    assert result.continued and result.continuation_reason == "missing_tail"
    assert tail_engine.calls == 2


@pytest.mark.parametrize("version", ["v2", "v3"])
def test_continuation_prompt_and_token_budget(tail_engine, monkeypatch, version):
    monkeypatch.setattr(config, "PROMPT_VERSION", version)
    calls = []
    original = tail_engine.__class__.__call__

    def record(self, prompt, **kwargs):
        calls.append((prompt, kwargs))
        return original(self, prompt, **kwargs)

    monkeypatch.setattr(tail_engine.__class__, "__call__", record)
    counts = iter([100, 8100])
    monkeypatch.setattr(generator, "count_prompt_tokens", lambda prompt: next(counts))
    result = generator.generate_cv_result("Synthetic CV")
    assert result.continued
    assert calls[1][0].startswith(calls[0][0])
    assert calls[1][0].endswith(',"skills":')
    assert calls[1][1]["max_tokens"] == 92
    assert calls[1][1]["stream"] is True


@pytest.mark.parametrize("enabled,version", [(False, "v3"), (True, "v1")])
def test_disabled_or_v1_does_not_continue(tail_engine, monkeypatch, enabled, version):
    monkeypatch.setattr(config, "CONTINUATION_ENABLED", enabled)
    monkeypatch.setattr(config, "PROMPT_VERSION", version)
    result = generator.generate_cv_result("Synthetic CV")
    assert tail_engine.calls == 1
    assert not result.continued


def test_context_overflow_skips_continuation(tail_engine, monkeypatch):
    counts = iter([100, state.context_tokens + 1])
    monkeypatch.setattr(generator, "count_prompt_tokens", lambda prompt: next(counts))
    result = generator.generate_cv_result("Synthetic CV")
    assert tail_engine.calls == 1
    assert not result.continued


def test_continuation_failure_preserves_first(tail_engine):
    tail_engine.outputs = tail_engine.outputs[:1]  # Second call raises IndexError.
    result = generator.generate_cv_result("Synthetic CV")
    assert json.loads(result.text) == profile_through("personal_projects")
    assert not result.continued


def test_second_truncation_is_salvaged_without_third_call(tail_engine, monkeypatch):
    monkeypatch.setattr(config, "LOOP_MAX_STRING_CHARS", 30)
    tail_engine.outputs[1] = '["Python"],"certificates":["' + 'x' * 100
    result = generator.generate_cv_result("Synthetic CV")
    assert result.continued
    assert json.loads(result.text)["skills"] == ["Python"]
    assert tail_engine.calls == 2


def test_first_long_string_is_planned_before_salvage(tail_engine, monkeypatch):
    monkeypatch.setattr(config, "LOOP_MAX_STRING_CHARS", 30)
    tail_engine.outputs[0] = ('{"personal_projects":[{"name":"Complete"},'
                              '{"description":["' + 'x' * 100)
    result = generator.generate_cv_result("Synthetic CV")
    assert result.continued and result.continuation_reason == "long_string"
    assert json.loads(result.text)["skills"] == ["Python"]
    assert tail_engine.calls == 2


def test_long_string_guard_cuts_inside_a_large_chunk(tail_engine, monkeypatch):
    monkeypatch.setattr(config, "LOOP_MAX_STRING_CHARS", 30)
    outputs = [json.dumps({"personal_projects": [
        {"name": "Complete"}, {"description": ["x" * 100]},
    ]}), tail_engine.outputs[1]]
    prompts = []

    def whole_chunks(self, prompt, **kwargs):
        prompts.append(prompt)
        text = outputs[self.calls]
        self.calls += 1
        return iter([{"choices": [{"text": text, "finish_reason": "stop"}]}])

    monkeypatch.setattr(tail_engine.__class__, "__call__", whole_chunks)
    result = generator.generate_cv_result("Synthetic CV")
    assert result.continued and result.continuation_reason == "long_string"
    assert '"description"' not in prompts[1][len(prompts[0]):]
    assert json.loads(result.text)["skills"] == ["Python"]
