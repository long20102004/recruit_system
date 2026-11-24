"""KB1 facts-only snapshot and offline parser/matching regression tests."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.kb.candidates import CandidateSkillFinder
from app.kb.store import KnowledgeBase
from kb.books import build_finder, count_mentions, detect_offset, parse_toc, related_skills

ROOT = Path(__file__).resolve().parents[2] / "kb"


def test_numbered_toc():
    sections = parse_toc("""Contents
1   Introduction                     1
    1.1   Running Python . . . . .    2
    1.2   Python values .........    5
\fiv   Contents
2   Functions                        9
    2.1   Calls . . . . . . . . .    9
A   Debugging                       20
    A.1   Errors . . . . . . . .    20
\fChapter 1
Introduction
1.1 This is body text, not a title  123
""", "sample")
    assert [s["id"] for s in sections] == [
        "sample:1", "sample:1.1", "sample:1.2", "sample:2", "sample:2.1", "sample:A", "sample:A.1"]
    assert sections[1] == dict(id="sample:1.1", title="Running Python", level=2,
                               page=2, parent="sample:1", mentions={})
    assert sections[0]["parent"] is None


def test_unnumbered_toc_continuations_and_appendix():
    sections = parse_toc("""Table of Contents
Preface . . . . . 1
Getting Started . . . . . 3
    About Version Control . . . . . 3
\f    A Short History of Git . . . . . 5
Git Basics . . . . . 9
    Repositories . . . . . 9
Appendix A: Other Tools . . . . . 20
    Editors . . . . . 21
\fIndex . . . . . 22
\fGetting Started
Do not store this paragraph.
""", "progit")
    assert [s["id"] for s in sections] == [
        "progit:1", "progit:1.1", "progit:1.2", "progit:2", "progit:2.1", "progit:A", "progit:A.1"]
    assert sections[2]["title"] == "A Short History of Git"
    assert sections[-2]["title"] == "Other Tools"


def test_no_toc_or_orphan_fails():
    with pytest.raises(ValueError, match="No table"):
        parse_toc("A paragraph without a contents page", "sample")
    with pytest.raises(ValueError, match="Orphan"):
        parse_toc("Contents\n  1.1 Orphan . . . . 3", "sample")


def test_offset_ignores_toc_rows():
    sections = [dict(title="First chapter", level=1, page=1),
                dict(title="Second chapter", level=1, page=3)]
    pages = ["Cover", "Contents\nFirst chapter  1\nSecond chapter  3",
             "Chapter 1\nFirst chapter\nSome text", "More text",
             "Chapter 2\nSecond chapter\nMore text"]
    assert detect_offset(sections, pages) == 2
    with pytest.raises(ValueError, match="offset"):
        detect_offset(sections, ["Missing headings"])


def test_mentions_counts_positions_and_deduplicates_aliases():
    finder = CandidateSkillFinder({"Git": "Git", "git version control": "Git",
                                   "Python": "Python", "pythonic": "Python",
                                   ".NET": ".NET", "C++": "C++"})
    # The raw Git and long alias overlap at one position, not two mentions.
    text = "  Git version control; Git GitHub git. Python PYTHON pythonic .NET .net C++ C++x"
    assert count_mentions(text, finder) == {".NET": 2, "C++": 1, "Git": 2, "Python": 3}
    assert count_mentions("", finder) == {}


def test_finder_omits_soft_skills_and_short_linker_aliases():
    kb = SimpleNamespace(skills={1: ("Python", "Programming Language"),
                                2: ("Communication", "Soft Skill"), 3: ("Git", "Tool/Platform")},
                         linker=SimpleNamespace(surfaces={"py": 1, "python3": 1,
                                                          "communication": 2, "git": 3}))
    assert count_mentions("Communication py python3 Git git", build_finder(kb)) == {"Git": 1, "Python": 1}


def test_related_counts_leaf_sections_not_frequency_or_chapter():
    sections = [dict(id="b:1", parent=None, mentions={"Python": 20, "Git": 20}),
                dict(id="b:1.1", parent="b:1", mentions={"Python": 3, "Git": 10}),
                dict(id="b:1.2", parent="b:1", mentions={"Python": 1}),
                dict(id="b:2", parent=None, mentions={"Python": 1, "Git": 1, "Java": 1})]
    assert related_skills("b", sections) == [dict(a="Git", b="Python", sections=2, source="b")]
    assert related_skills("b", sections[:2]) == []


def test_real_snapshot_schema_provenance_and_no_prose():
    raw = (ROOT / "sources/kb1_books.json").read_bytes()
    snapshot = json.loads(raw)
    assert set(snapshot) == {"books", "related"}
    kb = KnowledgeBase.from_csv(ROOT / "seed")
    names = {name for name, category in kb.skills.values() if category != "Soft Skill"}
    expected = {"progit": (13, 101), "thinkpython": (21, 218)}
    for book in snapshot["books"]:
        assert set(book) == {"id", "title", "authors", "edition", "licence", "url", "sha256", "sections"}
        sections = book["sections"]
        assert (sum(s["level"] == 1 for s in sections), sum(s["level"] == 2 for s in sections)) == expected[book["id"]]
        ids = {s["id"] for s in sections}
        assert len(ids) == len(sections)
        assert len(book["sha256"]) == 64
        assert any(s["mentions"] for s in sections)
        for section in sections:
            assert set(section) == {"id", "title", "level", "page", "parent", "mentions"}
            assert section["title"].strip() and section["page"] > 0
            assert section["level"] in {1, 2}
            assert section["parent"] in ids if section["level"] == 2 else section["parent"] is None
            assert set(section["mentions"]) <= names
            assert all(type(n) is int and n >= 1 for n in section["mentions"].values())
        assert [r for r in snapshot["related"] if r["source"] == book["id"]] == related_skills(book["id"], sections)

    def check_strings(value):
        if isinstance(value, str):
            assert len(value) <= 200
        elif isinstance(value, dict):
            for key, child in value.items():
                check_strings(key)
                check_strings(child)
        elif isinstance(value, list):
            for child in value:
                check_strings(child)

    check_strings(snapshot)
    manifest = json.loads((ROOT / "sources/MANIFEST.json").read_text())
    entry = next(e for e in manifest["files"] if e["file"] == "kb1_books.json")
    assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
    assert entry["prefix"] == "book"
    assert entry["pdf_sha256"] == {b["id"]: b["sha256"] for b in snapshot["books"]}
