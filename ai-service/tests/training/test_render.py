"""Pure renderer tests: no LibreOffice, network, models or real CV data."""

from copy import deepcopy
from html.parser import HTMLParser
import json

import pytest

from app.postprocess.text_match import contains, normalize
from training.synth.render import LAYOUTS, ground_label, load_profiles, render_html, validate_profile


@pytest.fixture
def record():
    return {
        "id": "fictional-001", "level": "middle", "lang": "en", "role": "Backend Developer",
        "profile": {
            "personal_info": {"full_name": "Nguyen Minh Fiction", "email": "fiction@example.com",
                              "phone": "0912 345 678", "github_url": "https://github.com/fiction-cv"},
            "objective": "Build reliable services & improve delivery <safely>.",
            "education": [{"school": "Fiction University", "major": "Computer Science",
                           "start_year": 2015, "end_year": 2019, "gpa": "3.45/4.0"}],
            "experience": [{"company": "Example Software", "job_title": "Backend Developer",
                            "start_date": "03/2021", "end_date": None,
                            "description": ["Built reliable payment services for many fictional customers.",
                                            "Reduced latency by 25% with improved database indexes."]}],
            "personal_projects": [{"name": "Fiction Ledger", "role": "Maintainer", "team_size": 4,
                                   "start_date": "04/2020", "end_date": "02/2021", "github_url": "github.com/fiction/ledger",
                                   "description": ["Created a fictional ledger with automated reconciliation checks."],
                                   "tech_stack": ["Java", "PostgreSQL", "React"]}],
            "skills": ["Java", "Go", "Spring Boot", "PostgreSQL"],
            "certificates": ["Cloud Engineer, Associate (2023)"],
            "honours": ["Excellent Contributor – Fiction Team 2022"],
            "languages": [{"language": "English", "note": "IELTS 7.0"},
                          {"language": "Vietnamese", "note": "Native"}],
        },
        "extras": {"headline": "Backend Engineer", "address": "Cau Giay, Ha Noi",
                   "dob": "14/02/1996", "linkedin": "linkedin.com/in/fiction-cv",
                   "skill_groups": [{"group": "Languages", "items": ["Java", "Go"]},
                                    {"group": "Backend", "items": ["Spring Boot", "PostgreSQL"]}],
                   "interests": ["Reading"]},
    }


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = False

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "head"):
            self.hidden = True

    def handle_endtag(self, tag):
        if tag in ("style", "script", "head"):
            self.hidden = False

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def html_text(content):
    parser = TextParser()
    parser.feed(content)
    return " ".join(parser.parts)


def leaves(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from leaves(child)
    elif isinstance(value, list):
        for child in value:
            yield from leaves(child)
    elif value is not None:
        yield str(value)


def test_valid(record):
    assert validate_profile(record) == []


@pytest.mark.parametrize("mutation,reason", [
    (lambda r: r["profile"].pop("honours"), "schema"),
    (lambda r: r["profile"]["experience"][0].pop("company"), "schema"),
    (lambda r: r["profile"]["education"][0].update(start_year="2015"), "schema"),
    (lambda r: r["profile"]["personal_projects"][0].update(team_size=True), "schema"),
    (lambda r: r["extras"]["skill_groups"][0]["items"].reverse(), "skill_groups_mismatch"),
    (lambda r: r["extras"].update(address="A\nB"), "multiline_string"),
    (lambda r: r["profile"]["languages"][0].update(language="Python (Advanced)"), "programming_language"),
    (lambda r: r.update(id="../escape"), "invalid_id"),
])
def test_invalid(record, mutation, reason):
    mutation(record)
    assert reason in validate_profile(record)


@pytest.mark.parametrize("bad", [None, [], 1, {}, {"profile": []}])
def test_invalid_shapes(bad):
    assert validate_profile(bad)


@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("lang", ["en", "vi"])
def test_layout_contains_all_label_values(record, layout, lang):
    record["lang"] = lang
    original = deepcopy(record)
    document = render_html(record, layout)
    text = html_text(document)
    for value in leaves(record["profile"]):
        assert value in text, (layout, value)
    for key in ("headline", "address", "dob", "linkedin"):
        assert record["extras"][key] in text
    assert ("Hiện tại" if lang == "vi" else "Present") in text
    assert "&lt;safely&gt;" in document
    assert "<safely>" not in document
    if layout != "L8":
        assert "Languages" in text
    label, dropped = ground_label(record["profile"], text)
    assert label == record["profile"]
    assert not dropped
    assert record == original


def test_layout_specifics(record):
    rendered = {layout: render_html(record, layout) for layout in LAYOUTS}
    assert "EXPERIENCE" in rendered["L1"] and "•" in rendered["L1"]
    assert 'class="sidebar"' in rendered["L2"]
    record["lang"] = "vi"
    assert "KINH NGHIỆM LÀM VIỆC" in render_html(record, "L3")
    assert "Example Software — Ha Noi | Backend Developer | 03/2021 - Present" in rendered["L4"]
    assert "Example Software, Ha Noi" in rendered["L5"]
    assert "<td>Languages</td><td>Java, Go</td>" in rendered["L6"]
    assert "Tech: Backend(Java, PostgreSQL), Frontend(React)" in rendered["L7"]
    assert "Languages: English (IELTS 7.0), Vietnamese (Native)" in rendered["L8"]
    assert "Certifications &amp; Awards" in rendered["L9"]
    assert "Certifications:</p>" in rendered["L9"] and "Awards:</p>" in rendered["L9"]
    assert 'class="timeline"' in rendered["L10"]
    with pytest.raises(ValueError):
        render_html(record, "L11")


def test_ground_missing_values_and_anchors(record):
    profile = record["profile"]
    original = deepcopy(profile)
    text = "English Nguyen Minh Fiction Java Example Software Backend Developer 03/2021"
    label, dropped = ground_label(profile, text)
    assert label["personal_info"]["email"] is None
    assert label["personal_info"]["full_name"] == "Nguyen Minh Fiction"
    assert label["objective"] is None
    assert label["education"] == label["personal_projects"] == []
    assert label["experience"][0]["description"] == []
    assert label["experience"][0]["end_date"] is None
    assert label["skills"] == ["Java"]
    assert label["languages"] == [{"language": "English", "note": None}]
    assert dropped["personal_info.email"] == 1
    assert dropped["experience.description"] == 2
    assert dropped["education.school"] == 1
    assert dropped["personal_projects.tech_stack"] == 3
    assert dropped["languages.language"] == 1
    assert dropped["languages.note"] == 2
    assert dropped["skills"] == 3
    assert not dropped["experience.end_date"]
    assert profile == original
    assert all(contains(normalize(text), value) for value in leaves(label))


def test_ground_empty_text_counts_every_discarded_leaf(record):
    label, dropped = ground_label(record["profile"], "")
    assert sum(dropped.values()) == len(list(leaves(record["profile"])))
    assert not list(leaves(label))
    assert label["personal_info"] == dict.fromkeys(record["profile"]["personal_info"])


def test_ground_keeps_anchor_but_removes_project_fields(record):
    label, dropped = ground_label(record["profile"], "Fiction Ledger Java")
    project = label["personal_projects"][0]
    assert project["name"] == "Fiction Ledger"
    for key in ("role", "team_size", "start_date", "end_date", "github_url"):
        assert project[key] is None
        assert dropped[f"personal_projects.{key}"] == 1
    assert project["description"] == []
    assert project["tech_stack"] == ["Java"]
    assert dropped["personal_projects.tech_stack"] == 2


def test_loader_sorted_skips_bad_and_duplicate(record, tmp_path):
    second = deepcopy(record)
    second["id"] = "a-001"
    (tmp_path / "z.jsonl").write_text(json.dumps(record) + "\n{bad\n" + json.dumps(record) + "\n", encoding="utf-8")
    (tmp_path / "a.jsonl").write_text(json.dumps(second) + "\n", encoding="utf-8")
    records, invalid = load_profiles(tmp_path)
    assert [r["id"] for r in records] == ["a-001", "fictional-001"]
    assert invalid == {"invalid_json": 1, "duplicate_id": 1}


def test_empty_profile_layouts(record):
    p = record["profile"]
    p["personal_info"] = dict.fromkeys(p["personal_info"])
    p["objective"] = None
    for key in p.keys() - {"personal_info", "objective"}:
        p[key] = []
    record["extras"]["skill_groups"] = []
    assert not validate_profile(record)
    for layout in LAYOUTS:
        assert "None" not in html_text(render_html(record, layout))
