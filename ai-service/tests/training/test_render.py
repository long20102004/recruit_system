"""Pure renderer tests: no LibreOffice, network, models or real CV data."""

from copy import deepcopy
from html.parser import HTMLParser
import json
import hashlib
from pathlib import Path

import pytest

from app.postprocess.text_match import contains, normalize
from training.synth.render import LAYOUTS, ground_label, layout_label, load_profiles, render_html, run, validate_profile


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
    expected = layout_label(record["profile"], layout)
    for value in leaves(expected):
        assert value in text, (layout, value)
    for key in ("headline", "address", "dob", "linkedin"):
        assert record["extras"][key] in text
    assert ("Hiện tại" if lang == "vi" else "Present") in text
    assert "&lt;safely&gt;" in document
    assert "<safely>" not in document
    if layout != "L8":
        assert ("NGOẠI NGỮ" if lang == "vi" and layout in ("L3", "L11", "L12", "L13", "L14") else "Languages") in text
    label, dropped = ground_label(expected, text)
    assert label == expected
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
        render_html(record, "L15")


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


def test_legacy_html_snapshots(record):
    # Captured from the unmodified renderer on the synthetic fixture above.
    hashes = [
        "0df4d20252b9f642cecb5c6538d6d6d1a78dbcc27949a6d962d4abfe3c45b798",
        "1031a6b08265286669fbe3ba9a7334d8c3b088a5c67742b1345928e4f3dbfa9c",
        "a0730dfae286ee142574875a77e02e14047920037cb645081389e0ac2abddac0",
        "a1e8aa13da739e19c4450e3ee5d504570de2fbd40db5bf6f111c97e4e549d7d8",
        "cc4d6c8c72ee87485fafa938a01d8d81bf786009380f66f5ae50476de17953ae",
        "67d351d3efbeb585165dc3dab9ab10a1815e8b17ae696e67952b5b4aec4321e1",
        "9b5dfd89105c931dd48d2e868e221e210f8ed59260c4cb1c9927a919160de1f2",
        "2336ae18d42201b1c03a39ce2accec56280f375028f342b0b8046348b1619ec2",
        "3d9b05354e23958e93aee28d309ebf62042f62b76e76b2eed600d63c9dfc3ba5",
        "7ca43188c1d4bf2e44d4e04ede6dfbda4af067b7c926101a35fd6bb35be32729",
    ]
    for i, expected in enumerate(hashes, 1):
        assert hashlib.sha256(render_html(record, f"L{i}").encode()).hexdigest() == expected


def test_sidebar_timeline(record):
    record["profile"]["experience"].append({
        "company": "Earlier Fiction", "job_title": "Developer", "start_date": "01/2019",
        "end_date": "02/2021", "description": ["Earlier fictional work."]})
    doc = render_html(record, "L11")
    assert 'width="38%"' in doc and 'width="58%"' in doc
    assert "page-break-before: always" in doc
    continuation = doc.split('<p class="continuation"')[1]
    assert "Work Experience" not in continuation
    assert continuation.index("02/2021") < continuation.index("Earlier Fiction") < continuation.index("01/2019")
    assert "Skills" in continuation and "Projects" in continuation
    assert "Present" in continuation and "Future" in continuation
    assert "- Description: " in doc and "- Technologies: Java, PostgreSQL, React" in doc
    assert '<strong>Cloud Engineer, Associate</strong></p><p class="record-date">2023</p><p>Java, Go, Spring Boot</p>' in doc


@pytest.mark.parametrize("layout", ["L11", "L12"])
def test_grouped_parentheses(record, layout):
    record["extras"]["skill_groups"] = [{"group": "Tools", "items": ["Head", "a", "b", "c", "X", "Y"]}]
    record["profile"]["skills"] = ["Head", "a", "b", "c", "X", "Y"]
    assert "Tools: Head (a, b, c), X, Y" in render_html(record, layout)
    assert layout_label(record["profile"], layout)["skills"] == record["profile"]["skills"]


def test_two_column_records(record):
    record["profile"]["honours"] = ["Fiction Award (2022)"]
    doc = render_html(record, "L13")
    assert 'width="47%"' in doc
    assert '<strong>Cloud Engineer, Associate</strong></p><p class="record-date">2023</p>' in doc
    assert '<strong>Fiction Award</strong></p><p class="record-date">(2022)</p>' in doc
    assert '<p>English</p><p>IELTS 7.0</p>' in doc
    assert layout_label(record["profile"], "L13")["honours"] == ["Fiction Award (2022)"]


@pytest.mark.parametrize("lang,career", [("en", "Career"), ("vi", "Quá trình làm việc")])
def test_projects_first(record, lang, career):
    record["lang"] = lang
    doc = render_html(record, "L14")
    assert doc.index("Fiction Ledger") < doc.index(career) < doc.index("Example Software") < doc.index("Fiction University")
    assert doc.rindex("</section>") == doc.index("</section>", doc.index("Fiction University"))


@pytest.mark.parametrize("layout", LAYOUTS)
def test_layout_labels(record, layout):
    original = deepcopy(record["profile"])
    record["profile"]["certificates"] += ["Fiction Expert (Associate)", "Fiction Cert (03/2020 - 04/2023)"]
    label = layout_label(record["profile"], layout)
    assert label["certificates"][1] == "Fiction Expert (Associate)"
    assert label["certificates"][0] == ("Cloud Engineer, Associate" if layout in ("L11", "L13") else original["certificates"][0])
    assert label["certificates"][2] == ("Fiction Cert" if layout in ("L11", "L13") else "Fiction Cert (03/2020 - 04/2023)")
    assert record["profile"]["certificates"][0] == original["certificates"][0]
    assert label is not record["profile"]


def test_pdf_only_rotation_without_backend(record, tmp_path, monkeypatch):
    import training.synth.render as renderer

    profiles = tmp_path / "profiles"
    profiles.mkdir()
    rows = []
    for i in range(5):
        r = deepcopy(record)
        r["id"] = f"fiction-{i}"
        rows.append(r)
    (profiles / "fiction.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    monkeypatch.setattr(renderer.shutil, "which", lambda _: "/fiction/soffice")

    def convert(command, **kwargs):
        work = Path(command[command.index("--outdir") + 1])
        for value in command[command.index("--outdir") + 2:]:
            (work / (Path(value).stem + ".pdf")).write_bytes(b"%PDF-fiction")

    monkeypatch.setattr(renderer.subprocess, "run", convert)
    monkeypatch.setattr(renderer, "extract_text", lambda *args: pytest.fail("backend called"))
    out = tmp_path / "out"
    result = run(profiles, out, "unused", layouts=("L11", "L12", "L13", "L14"), pdf_only=True)
    labels = [json.loads(line) for line in (out / "labels.jsonl").read_text().splitlines()]
    assert [r["layout"] for r in labels] == ["L11", "L12", "L13", "L14", "L11"]
    assert result["rendered"] == len(list((out / "pdf").glob("*.pdf"))) == 5
    assert not (out / "rendered.jsonl").exists()
    for row, source in zip(labels, rows):
        assert set(row) == {"id", "level", "lang", "layout", "output"}
        assert json.loads(row["output"]) == layout_label(source["profile"], row["layout"])


@pytest.mark.parametrize("layouts", [(), ("L15",), ("",)])
def test_invalid_layout_rotation(tmp_path, layouts):
    with pytest.raises(ValueError, match="Layouts"):
        run(tmp_path, tmp_path / "out", "unused", layouts=layouts)
