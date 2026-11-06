import json

from app.services.generator import generate_cv_result
from app.services.loop_guard import LoopGuard, salvage


def test_repeated_values_across_chunks():
    guard = LoopGuard(1200, 3)
    text = json.dumps({"items": ["a sufficiently long value"] * 3})
    assert any(guard.feed(char) for char in text)
    assert guard.reason == "repeated_value"


def test_long_string_and_escaped_quotes():
    guard = LoopGuard(10, 3)
    assert guard.feed(r'{"key":"abc\"defghijk')
    assert guard.reason == "long_string"


def test_normal_json_and_short_values():
    guard = LoopGuard(1200, 3)
    text = json.dumps({"items": ["Java"] * 10, "note": 'an escaped "quote"'})
    assert not any(guard.feed(char) for char in text)
    assert guard.reason is None


def test_salvage_deduplicates_and_drops_incomplete_string():
    text = '{"items":["same", "same", {"x":1}, {"x":1}, "unfinished'
    assert salvage(text) == {"items": ["same", {"x": 1}]}
    assert salvage('[1, 2]') is None


def test_generate_repeated_output(fake_engine):
    fake_engine.output = json.dumps({"items": ["a sufficiently long value"] * 4})
    result = generate_cv_result("synthetic input")
    assert result.truncated and result.reason == "repeated_value"
    assert json.loads(result.text) == {"items": ["a sufficiently long value"]}


def test_generate_normal_output(fake_engine):
    fake_engine.output = '{"items": ["Java", "Java"]}'
    result = generate_cv_result("synthetic input")
    assert not result.truncated and result.reason is None
    assert json.loads(result.text) == {"items": ["Java", "Java"]}


def test_same_value_in_different_lists_is_not_a_loop():
    """A technology in skills and in several tech stacks is normal (repeats count per list)."""
    guard = LoopGuard(2000, 3)
    profile = {"skills": ["Microsoft SQL Server"],
               "personal_projects": [{"tech_stack": ["Microsoft SQL Server"]} for _ in range(4)]}
    assert not any(guard.feed(char) for char in json.dumps(profile))
    assert guard.reason is None


def test_repeat_inside_nested_list_is_a_loop():
    guard = LoopGuard(2000, 3)
    text = json.dumps({"experience": [{"description": ["Built the same synthetic feature again"] * 3}]})
    assert any(guard.feed(char) for char in text)
    assert guard.reason == "repeated_value"
