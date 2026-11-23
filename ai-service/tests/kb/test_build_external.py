"""Offline public-source builder contracts with tiny artificial source fixtures."""
import csv
import hashlib
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from app.kb.keys import school_key, skill_key
from app.kb.store import KnowledgeBase
from kb.build_external import CATEGORIES, build_external, main
from kb.fetch_sources import Fetcher, USER_AGENT, survey_options, synthetic_vocabulary
from kb.load import read_seed, validate


def test_search_variants_preserve_and_split_public_options():
    from kb.fetch_sources import search_variants
    assert set(search_variants("HTML/CSS")) == {"HTML/CSS", "HTML", "CSS"}
    assert set(search_variants("Amazon Web Services (AWS)")) == {"Amazon Web Services (AWS)", "Amazon Web Services", "AWS"}
    assert set(search_variants("Express.js")) == {"Express.js", "Express"}


def test_gap_vocabulary_counts_spelling_variants_together():
    from kb.fetch_sources import gap_vocabulary
    assert gap_vocabulary({"Node.js": 1, "Nodejs": 1, "Python": 5, "Rare": 1}, {"Python"}) == ["Node.js", "Nodejs"]


def test_esco_compaction_keeps_only_reproducible_builder_fields():
    from kb.fetch_sources import compact_esco
    record = {"uri": "public", "className": "Skill", "skillReuseLevel": "transversal",
              "preferredLabel": {"en": "teamwork", "fr": "équipe"},
              "alternativeLabel": {"en": ["team-working"], "fr": ["travail"]},
              "description": {"en": "large unused text"},
              "_links": {"isInScheme": [{"uri": "scheme", "title": "unused"}],
                         "broaderOccupation": [{"uri": "http://data.europa.eu/esco/isco/C25"}],
                         "narrowerOccupation": [{"uri": "unused"}]}}
    compact = compact_esco(record)
    assert compact["preferredLabel"] == {"en": "teamwork"}
    assert compact["alternativeLabel"] == {"en": ["team-working"]}
    assert compact["_links"]["broaderOccupation"][0]["uri"].endswith("C25")
    assert "description" not in compact and "narrowerOccupation" not in compact["_links"]


def test_soft_skill_join_uses_public_alias_and_disambiguates(tmp_path):
    fetcher = Fetcher(tmp_path)
    (tmp_path / "wikidata_entities.json").write_text(json.dumps({"entities": {}}))
    (tmp_path / "esco_transversal.json").write_text(json.dumps({"records": [
        {"uri": "esco-team", "className": "Skill", "preferredLabel": {"en": "work in teams"},
         "alternativeLabel": {"en": ["team-working"]}}
    ]}))
    fetcher.sparql = lambda query: {"results": {"bindings": [
        {"item": {"value": "http://www.wikidata.org/entity/Q1"}},
        {"item": {"value": "http://www.wikidata.org/entity/Q2"}}]}}
    fetcher.json = lambda *args, **kwargs: {"entities": {
        "Q1": {**entity("teamwork", [], ["team-working", "Làm việc nhóm"]), "lastrevid": 1, "sitelinks": {"enwiki": {}}},
        "Q2": {**entity("teamwork", [], ["unrelated specialist sense"]), "lastrevid": 2, "sitelinks": {}},
    }}
    fetcher.soft_skills()
    data = json.loads((tmp_path / "wikidata_entities.json").read_text())
    assert data["soft_skill_ids"] == ["Q1"]
    assert data["esco_matches"] == {"Q1": "esco-team"}
    assert "Q2" not in data["entities"]


def test_combined_survey_soft_join_and_college(snapshots):
    sources, output = snapshots
    def replace(filename, edit):
        path = sources / filename
        data = json.loads(path.read_text())
        edit(data)
        path.write_text(json.dumps(data))
        manifest_path = sources / "MANIFEST.json"
        manifest = json.loads(manifest_path.read_text())
        next(e for e in manifest["files"] if e["file"] == filename)["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
    def wikidata(data):
        data["entities"].update({"Q20": entity("HTML", ["Q37045"]),
                                 "Q21": entity("CSS", ["Q317623"]),
                                 "Q22": entity("teamwork", [], ["Làm việc nhóm"])})
        data.update(survey_components={"HTML/CSS": ["Q20", "Q21"]}, soft_skill_ids=["Q22"],
                    esco_matches={"Q22": "http://data.europa.eu/esco/skill/team"})
    replace("wikidata_entities.json", wikidata)
    replace("stackoverflow_2026_technology.json", lambda d: d["Languages"]["data"].append({"response": "HTML/CSS"}))
    def college(data):
        data["query"] = "public country/class evidence"
        data["entities"]["Q30"] = entity("Synthetic College", [], ["SC"])
    replace("wikidata_vn_universities.json", college)
    build_external(sources, output)
    kb = KnowledgeBase.from_csv(output)
    assert kb.linker.link("HTML")[0].name == "HTML"
    assert kb.linker.link("CSS")[0].name == "CSS"
    assert kb.linker.link("teamwork")[0].name == "work in teams"
    assert kb.linker.link("Làm việc nhóm")[0].category == "Soft Skill"
    assert kb.link_school("Synthetic College (SC)")[1] == "Synthetic College"


def test_school_geographic_comma_qualifiers_do_not_merge(snapshots):
    sources, output = snapshots
    school_path = sources / "wikidata_vn_universities.json"
    school_path.write_text(json.dumps({"query": "public country/class evidence", "entities": {
        "Q31": entity("Institute of Technology, Hanoi", [], ["ITHN"]),
        "Q32": entity("Institute of Technology, Ho Chi Minh City", [], ["ITHCM"]),
    }}))
    manifest_path = sources / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    next(e for e in manifest["files"] if e["file"] == school_path.name)["sha256"] = hashlib.sha256(school_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    build_external(sources, output)
    kb = KnowledgeBase.from_csv(output)
    assert kb.link_school("ITHN")[0] != kb.link_school("ITHCM")[0]


def entity(name, classes, aliases=(), claims=None):
    return {"labels": {"en": {"value": name}}, "aliases": {"en": [{"value": a} for a in aliases]},
            "claims": claims or {}, "accepted_classes": classes}


def claim(qid):
    return {"mainsnak": {"datavalue": {"value": {"id": qid}}}}


@pytest.fixture
def snapshots(tmp_path):
    sources, output = tmp_path / "sources", tmp_path / "seed"
    sources.mkdir()
    output.mkdir()
    (output / "section_headings.csv").write_text("heading,section\nSKILLS,SKILLS\n")
    (output / "university_alias_blocklist.csv").write_text("alias,reason\nBlocked,ambiguous\n")
    files = {
        "stackoverflow_2025_technology.json": ({"Language": {"datasets": {"Language": {"data": [{"response": "Python"}]}}},
                                               "Webframe": {"datasets": {"Webframe": {"data": [{"response": "React"}, {"response": "Other"}]}}}}, "stackoverflow-2025"),
        "stackoverflow_2026_technology.json": ({"Languages": {"meta": {"question": "Languages"}, "data": [{"response": "Python"}, {"response": "C#"}, {"response": "Other"}, {"response": "All Respondents"}]},
                                               "WebFramework": {"data": [{"response": "React"}, {"response": "Django"}]},
                                               "LLM": {"data": [{"response": "Not a skill"}]}}, "stackoverflow-2026"),
        "wikidata_entities.json": ({"entities": {
            "Q1": entity("Python", ["Q9143"], ["Py", "shared"], {"P361": [claim("Q2")]}),
            "Q2": entity("React", ["Q188860"], ["ReactJS", "shared"], {"P277": [claim("Q1")], "P527": [claim("Q3")]}),
            "Q3": entity("Django", ["Q1330336"], claims={"P277": [claim("Q1")], "P361": [claim("Q2")]}),
            "Q4": entity("Extra Library", ["Q188860"], ["Extra Lib"]),
        }, "survey_matches": {"Python": "Q1", "React": "Q2", "Django": "Q3"}, "gap_fill_ids": ["Q4"]}, "wikidata"),
        "wikidata_vn_universities.json": ({"entities": {
            "Q10": entity("Synthetic Institute", [], ["SI", "Blocked"]),
            "Q11": entity("Completely Other Academy", [], ["SI", "Must Not Become An Alias"]),
        }}, "wikidata"),
        "esco_transversal.json": ({"roots": ["root"], "records": [
            {"uri": "root", "className": "Concept"},
            {"uri": "http://data.europa.eu/esco/skill/team", "className": "Skill", "preferredLabel": {"en": "work in teams"}, "alternativeLabel": {"en": ["teamworking"]}},
        ]}, "esco"),
        "esco_occupations.json": ({"roots": ["C25", "C35"], "records": [
            {"uri": "http://data.europa.eu/esco/occupation/developer", "preferredLabel": {"en": "software developer"}, "alternativeLabel": {"en": ["programmer"]}},
        ]}, "esco"),
        "languages.yml": ('Python:\n  aliases:\n  - python3\n  - cake\nC#:\n  aliases:\n  - csharp\n', "linguist"),
        "vn_universities.csv": ("name_vi,name_en,abbreviation,group\nHọc viện Tổng hợp,Synthetic Institute,SI,\nTrường Một,First School,DU,\nTrường Hai,Second School,DU,\n", "wikipedia"),
    }
    manifest = {"files": [], "unavailable": []}
    for filename, (content, prefix) in files.items():
        data = (json.dumps(content) if isinstance(content, dict) else content).encode()
        (sources / filename).write_bytes(data)
        manifest["files"].append({"file": filename, "prefix": prefix, "sha256": hashlib.sha256(data).hexdigest(),
                                  "url": "https://example.org/" + filename, "version": "75654510" if prefix == "wikipedia" else "fixture",
                                  "retrieved": "2026-11-05", "licence": "CC0 1.0", "attribution": "Artificial fixture"})
    (sources / "MANIFEST.json").write_text(json.dumps(manifest))
    return sources, output


def test_build_offline_and_deterministic(snapshots):
    sources, output = snapshots
    section = (output / "section_headings.csv").read_bytes()
    with patch("requests.sessions.Session.request", side_effect=AssertionError("Offline build")):
        summary = build_external(sources, output)
        before = {p.name: p.read_bytes() for p in output.iterdir()}
        assert build_external(sources, output) == summary
        assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    assert (output / "section_headings.csv").read_bytes() == section
    seed = read_seed(output)
    assert validate(seed) == []
    assert [r["name"] for r in seed["categories"]] == CATEGORIES
    names = {r["name"]: r for r in seed["skills"]}
    assert "Other" not in names and "Not a skill" not in names
    assert names["Python"]["source"] == "stackoverflow-2026:Languages"
    assert names["Extra Library"]["source"] == "wikidata:Q4"
    assert names["work in teams"]["category"] == "Soft Skill"
    aliases = {r["alias_key"]: r for r in seed["skill_aliases"]}
    assert "shared" not in aliases and "cake" not in aliases
    assert summary["alias_collisions"] == 1
    assert aliases["python3"]["source"] == "linguist:Python"
    assert aliases["react"]["skill_id"] == names["React"]["id"]
    assert all(r["alias_key"] == skill_key(r["surface"]) for r in seed["skill_aliases"])
    assert {r["name"] for r in seed["job_titles"]} == {"software developer", "programmer"}
    assert summary["cycle_edges_dropped"] >= 1
    edges = {(r["src_id"], r["rel"], r["dst_id"]) for r in seed["skill_edges"]}
    assert (names["Django"]["id"], "REQUIRES", names["Python"]["id"]) in edges
    assert (names["Django"]["id"], "PART_OF", names["React"]["id"]) in edges
    school_aliases = {r["alias_key"] for r in seed["university_aliases"]}
    assert "du" not in school_aliases and "blocked" not in school_aliases
    assert "must not become an alias" not in school_aliases
    assert "si" in school_aliases
    kb = KnowledgeBase.from_csv(output)
    assert kb.link_school("SI")[1] == "Học viện Tổng hợp"
    assert kb.linker.link("Extra Lib")[0].name == "Extra Library"


def test_checksum_failure_is_not_silent(snapshots):
    sources, output = snapshots
    (sources / "languages.yml").write_text("tampered")
    with pytest.raises(ValueError, match="checksum"):
        build_external(sources, output)


def test_snapshot_symlink_cannot_escape_sources(snapshots):
    sources, output = snapshots
    snapshot = sources / "languages.yml"
    outside = sources.parent / "outside.yml"
    outside.write_bytes(snapshot.read_bytes())
    snapshot.unlink()
    snapshot.symlink_to(outside)
    with pytest.raises(ValueError, match="outside sources"):
        build_external(sources, output)


def test_cli(snapshots, capsys):
    sources, output = snapshots
    main(["--sources", str(sources), "--out", str(output)])
    assert json.loads(capsys.readouterr().out)["skills"] > 0


def test_survey_formats_ignore_metadata():
    assert list(survey_options({"Languages": {"meta": {"question": "Do not import me"}, "data": [{"response": "Python"}]}})) == [("Python", "Languages", "Programming Language")]
    assert list(survey_options({"Language": {"datasets": {"Learning to Code": {"name": "Learning to Code", "data": [{"response": "Go"}]}}}})) == [("Go", "Language", "Programming Language")]


def test_synthetic_vocabulary_only_approved_paths(tmp_path):
    approved = tmp_path / "data/clean"
    approved.mkdir(parents=True)
    (approved / "silver_dataset.jsonl").write_text(json.dumps({"input": "NEVER COPY", "output": json.dumps({"skills": ["Python"], "personal_projects": [{"tech_stack": ["Django"]}]})}) + "\n")
    forbidden = tmp_path / "data/real_test"
    forbidden.mkdir(parents=True)
    (forbidden / "private.jsonl").write_text("INVALID MUST NOT READ")
    assert synthetic_vocabulary(tmp_path) == {"Python": 1, "Django": 1}


def test_fetch_http_retry_user_agent_and_cache(tmp_path):
    fetcher = Fetcher(tmp_path)
    assert fetcher.session.headers["User-Agent"] == USER_AGENT
    from unittest.mock import Mock
    limited, success = Mock(status_code=429, headers={"Retry-After": "1"}), Mock(status_code=200)
    fetcher.session.get = Mock(side_effect=[limited, success])
    with patch("kb.fetch_sources.time.sleep") as sleep:
        assert fetcher.get("https://example.org") is success
        sleep.assert_any_call(1.0)
    fetcher.save("snapshot.json", {"public": True}, url="https://example.org", version="1", licence="CC0", attribution="Test", prefix="test")
    assert fetcher.cached("snapshot.json")
    (tmp_path / "snapshot.json").write_text("tampered")
    assert not fetcher.cached("snapshot.json")


def test_wikidata_requires_class_evidence_and_public_name(tmp_path):
    fetcher = Fetcher(tmp_path)

    def api(url, **params):
        if params["action"] == "wbsearchentities":
            return {"search": [{"id": "Q1"}, {"id": "Q2"}, {"id": "Q3"}]}
        return {"entities": {
            "Q1": {**entity("Python", ["Q9143"]), "sitelinks": {"enwiki": {}}, "lastrevid": 123},
            "Q2": {**entity("Unrelated software", ["Q7397"]), "sitelinks": {}},
        }}

    evidence = [{"item": {"value": "http://www.wikidata.org/entity/" + q},
                 "root": {"value": "http://www.wikidata.org/entity/Q7397"}} for q in ("Q1", "Q2")]
    fetcher.json = api
    fetcher.sparql = lambda query: {"results": {"bindings": evidence}}
    fetcher.wikidata([("Python", True), ("SYNTHETIC_LABEL_NEVER_PERSIST", False)])
    result = json.loads((tmp_path / "wikidata_entities.json").read_text())
    assert set(result["entities"]) == {"Q1"}
    assert result["survey_matches"] == {"Python": "Q1"}
    assert result["gap_fill_ids"] == []
    assert len(result["class_evidence"]) == 1
    assert "SYNTHETIC_LABEL_NEVER_PERSIST" not in (tmp_path / "wikidata_entities.json").read_text()


def test_wikidata_refresh_extension_preserves_verified_base(snapshots):
    sources, _ = snapshots
    fetcher = Fetcher(sources, refresh=True)
    fetcher.json = lambda *args, **kwargs: {"entities": {
        "Q4": {**entity("Extra Library", ["Q188860"]), "lastrevid": 100, "sitelinks": {}}
    }}
    fetcher.sparql = lambda query: {"results": {"bindings": [
        {"item": {"value": "http://www.wikidata.org/entity/Q4"},
         "root": {"value": "http://www.wikidata.org/entity/Q188860"}}]}}
    fetcher.wikidata([("Extra Library", False)], extend=True)
    data = json.loads((sources / "wikidata_entities.json").read_text())
    assert set(data["entities"]) == {"Q1", "Q2", "Q3", "Q4"}
    assert data["survey_matches"] == {"Python": "Q1", "React": "Q2", "Django": "Q3"}


def test_esco_bulk_walk_includes_all_narrower_relations(tmp_path):
    fetcher = Fetcher(tmp_path)
    calls = []

    def api(url, **params):
        calls.append(params)
        uris = params["uris"].split(",")
        records = {}
        for uri in uris:
            links = {"narrowerConcept": [{"uri": "child1"}], "narrowerSkill": [{"uri": "child2"}]} if uri == "root" else {}
            if uri == "child2":
                links = {"isInScheme": [{"uri": "http://data.europa.eu/esco/concept-scheme/member-skills"}],
                         "narrowerSkill": [{"uri": "occupation-specific-not-transversal"}]}
            records[uri] = {"uri": uri, "_links": links, "preferredLabel": {"en": uri}}
        return {"_embedded": records}

    fetcher.json = api
    fetcher.esco_tree("esco.json", ["root"], "skill")
    result = json.loads((tmp_path / "esco.json").read_text())
    assert {r["uri"] for r in result["records"]} == {"root", "child1", "child2"}
    assert len(calls) == 2 and calls[1]["uris"] == "child1,child2"
    assert all(call["selectedVersion"] == result["selectedVersion"] for call in calls)


def test_manifest_pins_entity_revisions_without_refetch(tmp_path):
    fetcher = Fetcher(tmp_path)
    fetcher.save("wikidata_entities.json", {"entities": {"Q1": {"lastrevid": 123, "labels": {}}}},
                 url="https://www.wikidata.org/w/api.php", version="test", licence="CC0 1.0",
                 attribution="Wikidata contributors", prefix="wikidata")
    with patch.object(fetcher, "json", side_effect=AssertionError("Already pinned")):
        fetcher.finish_wikidata("wikidata_entities.json")
        before = (tmp_path / "wikidata_entities.json").read_bytes()
        fetcher.finish_wikidata("wikidata_entities.json")
    assert before == (tmp_path / "wikidata_entities.json").read_bytes()
    assert fetcher.manifest["files"][0]["revision"] == {"Q1": 123}


def test_legacy_cli_refuses_training_inputs():
    from kb.build_seed import main as legacy_main
    with pytest.raises(SystemExit):
        legacy_main(["--train", "must-not-be-read.jsonl"])


def test_real_seed_provenance_and_snapshot_integrity():
    root = Path(__file__).resolve().parents[2] / "kb"
    manifest = json.loads((root / "sources/MANIFEST.json").read_text())
    prefixes = {e["prefix"] for e in manifest["files"]}
    for entry in manifest["files"]:
        assert all(entry.get(key) for key in ("file", "url", "retrieved", "version", "sha256", "licence", "attribution"))
        assert hashlib.sha256((root / "sources" / entry["file"]).read_bytes()).hexdigest() == entry["sha256"]
    seed = read_seed(root / "seed")
    assert validate(seed) == []
    wd = json.loads((root / "sources/wikidata_entities.json").read_text())
    schools = json.loads((root / "sources/wikidata_vn_universities.json").read_text())
    qids = set(wd["entities"]) | set(schools["entities"])
    esco = {}
    for filename in ("esco_transversal.json", "esco_occupations.json"):
        esco.update({r["uri"]: r for r in json.loads((root / "sources" / filename).read_text())["records"]})
    from kb.build_external import linguist_languages
    languages = linguist_languages(root / "sources/languages.yml")
    surveys = {str(year): json.loads((root / f"sources/stackoverflow_{year}_technology.json").read_text())
               for year in (2024, 2025, 2026) if (root / f"sources/stackoverflow_{year}_technology.json").exists()}
    options = {year: {(name, question) for name, question, _ in survey_options(doc)} for year, doc in surveys.items()}
    for table in ("skills", "skill_aliases", "skill_edges", "categories", "universities", "university_aliases", "job_titles"):
        assert seed[table], f"Empty real table: {table}"
        for row in seed[table]:
            assert row["source"].strip(), (table, row)
            assert row["source"].split(":", 1)[0] in prefixes
            prefix, reference = row["source"].split(":", 1)
            if prefix == "wikidata":
                assert reference.split(":")[0] in qids
                if table == "skills":
                    # Display name = the public label (sentence case) or one of the entity's own
                    # public surfaces (survey spelling such as "CSS" for "Cascading Style Sheets").
                    from app.kb.keys import skill_key
                    from kb.build_external import entity_surfaces
                    entity = wd["entities"][reference]
                    label = entity["labels"]["en"]["value"]
                    assert (row["name"] in {label, label[:1].upper() + label[1:]}
                            or skill_key(row["name"]) in {skill_key(x) for x in entity_surfaces(entity)})
            elif prefix == "esco":
                assert reference in esco
                if table in {"skills", "skill_aliases", "job_titles"}:
                    record = esco[reference]
                    surfaces = [record["preferredLabel"]["en"], *record.get("alternativeLabel", {}).get("en", [])]
                    assert row.get("surface", row.get("name")) in surfaces
            elif prefix == "linguist":
                assert reference in languages
                if table == "skill_aliases":
                    assert row["surface"] in languages[reference].get("aliases", [])
            elif prefix == "wikipedia":
                assert reference == "vi:75654510"
            elif prefix == "institution":
                official = json.loads((root / "sources/official_vn_colleges.json").read_text())
                records = [r for r in official["records"] if r["url"].split("/")[2] == reference]
                assert records
                if table == "universities":
                    assert row["name"] in {r["name"] for r in records}
                if table == "university_aliases":
                    short = {school_key(re.sub(r"^(Trường\s+)?Cao\s+đẳng\s+", "", r["name"], flags=re.I)) for r in records}
                    assert row["alias_key"] in ({school_key(r["name"]) for r in records} | short
                                                | {k + " college" for k in short})
            elif prefix == "stackoverflow-tags":
                tags = {r["tag"]: r for r in json.loads((root / "sources/stackoverflow_tags.json").read_text())["records"]}
                assert reference in tags
                if table == "skill_aliases":
                    r = tags[reference]
                    assert row["surface"] in {r["display"], r["tag"], r["tag"].replace("-", " "), *r["synonyms"]}
            else:
                year = prefix.split("-")[1]
                assert reference in surveys[year]
                if table in {"skills", "skill_aliases"}:
                    surface = row.get("surface", row.get("name"))
                    published = set(options[year])
                    if table == "skill_aliases":
                        for name, question in options[year]:
                            acronym = re.fullmatch(r"(.+) \(([A-Z0-9-]{2,})\)", name)
                            if acronym:
                                published.update((part, question) for part in acronym.groups())
                    assert (surface, reference) in published
    for row in seed["skill_edges"]:
        _, qid, prop = row["source"].split(":")
        assert prop in {"P277", "P361", "P527"}
        assert wd["entities"][qid]["claims"][prop]
