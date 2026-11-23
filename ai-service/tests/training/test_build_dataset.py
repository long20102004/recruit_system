import argparse
import json
import sys
import types

import pytest

from app.services.prompt_v2 import END_OF_TURN, HINTS_HEADER, TOP_KEYS, render_prompt
from training import build_dataset


def make_record(index):
    name = f"Synthetic Person {index}"
    company = f"Synthetic Company {index}"
    school = f"Synthetic University {index}"
    cv = (f"{name}\n{company}\n{school}\nJava\nCloud Certificate\n"
          "Merit Award\nEnglish\nBuilt reliable systems")
    profile = {
        "personal_info": {"full_name": name, "email": None, "phone": None, "github_url": None},
        "objective": None,
        "education": [{"school": school, "major": None, "start_year": None, "end_year": None, "gpa": None}],
        "experience": [{"company": company, "job_title": None, "start_date": None,
                        "end_date": None, "description": ["Built reliable systems", "Invented invisible rockets"]}],
        "personal_projects": [],
        "skills": ["Java", "ImaginarySkill"],
        "certificates": ["Cloud Certificate", "Imaginary Certificate"],
        "honours": ["Merit Award", "Imaginary Award"],
        "languages": [{"language": "English", "note": None}, {"language": "Japanese", "note": None}],
    }
    return {"instruction": "", "input": cv, "output": json.dumps(profile, ensure_ascii=False, indent=2)}


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def dataset(tmp_path, monkeypatch):
    data = tmp_path / "data"
    silver = [make_record(i) for i in range(8)]
    val = [silver[0], make_record(8)]
    val_swap = [make_record(9), make_record(10)]
    write_jsonl(data / "clean" / "silver_dataset.jsonl", silver)
    write_jsonl(data / "clean" / "val.jsonl", val)
    write_jsonl(data / "val_swap.jsonl", val_swap)
    monkeypatch.setattr(build_dataset, "DEV_SIZE", 2)
    args = argparse.Namespace(data=data, out=tmp_path / "out", hints=False,
                              kb_seed=tmp_path / "seed", tokenizer=None, max_len=4096)
    return args, silver, val, val_swap


def completion(row):
    assert row["completion"].endswith(END_OF_TURN)
    return json.loads(row["completion"][:-len(END_OF_TURN)])


def test_build_dataset_splits_cleaning_augmentation_and_privacy(dataset):
    args, silver, val, val_swap = dataset
    summary = build_dataset.build(args)
    splits = {name: read_jsonl(args.out / f"{name}.jsonl")
              for name in ("train", "dev", "val", "val_swap")}
    held_out = {r["input"] for r in val + val_swap}
    assert not {r["input"] for name in ("train", "dev") for r in splits[name]} & held_out
    assert summary["label_cleaning"]["pool_skipped_val_or_duplicate"] == 1

    pool = len(silver) - 1
    assert len(splits["dev"]) == 2
    assert len(splits["train"]) == 2 * (pool - 2)
    assert summary["label_cleaning"]["train_augmented"] == pool - 2
    for field in ("skills", "certificates", "honours", "languages", "experience_bullets"):
        assert summary["label_cleaning"][f"removed_ungrounded_{field}"] == pool

    for row in splits["train"] + splits["dev"]:
        profile = completion(row)
        assert profile["skills"] == ["Java"]
        assert profile["certificates"] == ["Cloud Certificate"]
        assert profile["honours"] == ["Merit Award"]
        assert profile["languages"] == [{"language": "English", "note": None}]
        assert profile["experience"][0]["description"] == ["Built reliable systems"]

    original_inputs = {r["input"] for r in silver}
    originals = {completion(r)["personal_info"]["full_name"]: r for r in splits["train"]
                 if r["input"] in original_inputs}
    augmented = [r for r in splits["train"] if r["input"] not in original_inputs]
    assert len(originals) == len(augmented) == pool - 2
    for row in augmented:
        profile = completion(row)
        original = originals[profile["personal_info"]["full_name"]]
        company = profile["experience"][0]["company"]
        assert row["input"] != original["input"]
        assert company in row["input"]
        assert company != completion(original)["experience"][0]["company"]

    for rows in splits.values():
        for row in rows:
            assert row["prompt"] == render_prompt(row["input"])
            assert list(completion(row)) == list(TOP_KEYS)
    for name, source in (("val", val), ("val_swap", val_swap)):
        assert [(r["input"], r["output"]) for r in splits[name]] == [
            (r["input"], r["output"]) for r in source]

    summary_text = (args.out / "summary.json").read_text(encoding="utf-8")
    assert json.loads(summary_text) == summary
    for record in silver + val + val_swap:
        profile = json.loads(record["output"])
        assert profile["personal_info"]["full_name"] not in summary_text
        assert profile["experience"][0]["company"] not in summary_text

    def assert_numeric_leaves(value):
        if isinstance(value, dict):
            for child in value.values():
                assert_numeric_leaves(child)
        else:
            assert isinstance(value, (int, float, bool))

    assert_numeric_leaves(summary)


def test_build_dataset_with_hints(dataset, monkeypatch):
    args, _, _, _ = dataset
    calls = []

    class Finder:
        @classmethod
        def from_csv(cls, path):
            calls.append(path)
            return cls()

        def find(self, cv):
            assert cv
            return ["Java"]

    module = types.ModuleType("app.kb.candidates")
    module.CandidateSkillFinder = Finder
    monkeypatch.setitem(sys.modules, "app.kb.candidates", module)
    args.hints = True
    summary = build_dataset.build(args)
    assert calls == [args.kb_seed]
    assert summary["hints"] is True
    for name in ("train", "dev", "val", "val_swap"):
        for row in read_jsonl(args.out / f"{name}.jsonl"):
            assert row["prompt"] == render_prompt(row["input"], ["Java"])
            assert f"{HINTS_HEADER} Java{END_OF_TURN}" in row["prompt"]
