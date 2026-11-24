"""Fetch public, attributable KB snapshots. Never persist synthetic input vocabulary.

Run from ai-service: .venv/bin/python -m kb.fetch_sources
Existing verified snapshots are reused; --refresh explicitly retrieves them again.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import json
import re
from pathlib import Path
import time

import requests

from app.kb.keys import skill_key

ROOT = Path(__file__).resolve().parent
USER_AGENT = "recruit-system-kb-builder/1.0 (https://github.com/long20102004/recruit_system)"
WD_API = "https://www.wikidata.org/w/api.php"
SE_API = "https://api.stackexchange.com/2.3"
# A Stack Overflow tag is accepted as a skill only when it is an established tag.
MIN_TAG_COUNT = 500


def tag_variants(term):
    """Stack Overflow tag spellings of a vocabulary term ("Spring MVC" -> spring-mvc, springmvc)."""
    t = re.sub(r"\s*\([^)]*\)", "", term.strip().lower())
    base = re.sub(r"[\s_]+", "-", t)
    out = {base, base.replace("-", ""), base.replace("/", "-"), base.replace("/", ""), base.replace(".", "")}
    return sorted(v for v in out if re.fullmatch(r"[a-z0-9#+.-]{2,35}", v))
SPARQL = "https://query.wikidata.org/sparql"
ESCO = "https://ec.europa.eu/esco/api"
ESCO_VERSION = "v1.2.1"
# Explicit software/computing roots; membership is verified by SPARQL, not descriptions.
TECH_CLASSES = {
    "Q7397": "Tool/Platform", "Q9143": "Programming Language",
    "Q271680": "Framework/Library", "Q188860": "Framework/Library",
    "Q176165": "Database", "Q1330336": "Framework/Library",
    "Q66747126": "Methodology/Concept", "Q8366": "Methodology/Concept",
    "Q9135": "Tool/Platform", "Q483639": "Cloud",
    "Q37045": "Programming Language",
    "Q188267": "Methodology/Concept", "Q846636": "Methodology/Concept",
    "Q635346": "Methodology/Concept", "Q181156": "Methodology/Concept",
    "Q188522": "Testing/QA", "Q317623": "Methodology/Concept",
    "Q681263": "Methodology/Concept", "Q494823": "Methodology/Concept",
    "Q1378470": "Methodology/Concept",
    "Q123370638": "Data/AI",  # branch of computer science (verified English label)
    "Q235557": "Methodology/Concept", "Q845739": "Programming Language",
    "Q190686": "Methodology/Concept", "Q190637": "Design/UI-UX",
    "Q65938634": "Testing/QA",
}
SELECTION_VERSION = 5
# Public search prompts only: none becomes a seed label without source evidence.
PUBLIC_TECH_QUERIES = "HTML|CSS|HTML5|CSS3|SCSS|AWS|Docker Compose|Node.js|Express.js|Spring MVC|Spring Data JPA|Hibernate|JPA|Lombok|Thymeleaf|Entity Framework|LINQ|AutoMapper|SignalR|Material-UI|MUI|Bootstrap|Postman|MySQL Workbench|Anaconda|Photoshop|Illustrator|Microsoft Excel|Microsoft Word|Microsoft PowerPoint|Figma|Lark|Lumen|Sequelize|Mockito|JUnit|object-oriented programming|MVC|model-view-controller|microservices|event-driven architecture|CI/CD|continuous integration|continuous delivery|dependency injection|unit testing|machine learning|JSON Web Token|stored procedure|responsive web design|Agile|Scrum|Kanban".split("|")
SOFT_QUERIES = "teamwork|communication|problem solving|time management|adaptability|autodidacticism|presentation".split("|")


def search_variants(name):
    variants = {name.strip()}
    variants.update(p.strip() for p in name.split("/") if p.strip())
    match = re.fullmatch(r"(.+?)\s*\(([^()]+)\)", name)
    if match:
        variants.update(s.strip() for s in match.groups())
    variants.add(re.sub(r"(?:\.js|JS)$", "", name).strip())
    return sorted(v for v in variants if v)


def compact_esco(record):
    result = {k: record[k] for k in ("uri", "className", "skillReuseLevel") if k in record}
    for field in ("preferredLabel", "alternativeLabel", "altLabels"):
        if "en" in record.get(field, {}):
            result[field] = {"en": record[field]["en"]}
    result["_links"] = {k: [{"uri": v["uri"]} for v in (values if isinstance(values, list) else [values])]
                        for k, values in record.get("_links", {}).items()
                        if k in {"isInScheme", "broaderConcept", "broaderOccupation", "broaderSkill"}}
    return result
QUESTION_CATEGORIES = {
    "Language": "Programming Language", "Languages": "Programming Language",
    "Database": "Database", "Databases": "Database", "Platform": "Cloud",
    "CloudPlat": "Cloud", "Webframe": "Framework/Library",
    "WebFramework": "Framework/Library", "DevEnvs": "Tool/Platform",
    "DevIDE": "Tool/Platform", "CodeTest": "Testing/QA",
    "OfficeStackAsync": "Tool/Platform", "KnowMgmt": "Tool/Platform",
    "SecOps": "Security", "OpSys": "Tool/Platform",
    "NEWCollabTools": "Tool/Platform", "ToolsTech": "DevOps/CI-CD",
    "MiscTech": "Framework/Library", "Embedded": "Tool/Platform",
    "EntSearch": "Tool/Platform",
}


def survey_options(document):
    """Only technology question data, never dataset names, series or meta labels."""
    for question, category in QUESTION_CATEGORIES.items():
        block = document.get(question, {})
        datasets = block.get("datasets", {})
        rows = block.get("data", []) if not datasets else [
            r for dataset in datasets.values() for r in dataset.get("data", [])
        ]
        names = {r.get("response", "").strip() for r in rows}
        for name in sorted(names):
            if name and name.casefold() not in {
                "other", "other (please specify)", "none", "none of the above",
                "learning to code", "all respondents", "professional developers",
                "not applicable", "na", "n/a",
            } and not name.casefold().startswith(("other (", "other ")):
                yield name, question, category


def synthetic_vocabulary(service_dir: Path) -> Counter:
    """Read ONLY approved synthetic labels, in memory; no CV text is inspected."""
    counts = Counter()
    paths = [service_dir / "data/clean/silver_dataset.jsonl"]
    paths += sorted((service_dir / "data/synth_v3/profiles").glob("*.jsonl"))

    def labels(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"skills", "tech_stack"} and isinstance(child, list):
                    counts.update(s.strip() for s in child if isinstance(s, str) and s.strip())
                elif key not in {"input", "text", "cv_text"}:
                    labels(child)
        elif isinstance(value, list):
            for child in value:
                labels(child)

    for path in paths:
        if path.exists():
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    output = obj.get("output", obj)
                    if isinstance(output, str):
                        try:
                            output = json.loads(output)
                        except ValueError:
                            continue
                    labels(output)
    return counts


def gap_vocabulary(vocabulary, survey_names):
    """Aggregate approved label counts across files and spelling variants."""
    grouped = {}
    survey_keys = {skill_key(name) for name in survey_names}
    for name, count in vocabulary.items():
        grouped.setdefault(skill_key(name), Counter())[name] += count
    return sorted(name for key, counts in grouped.items()
                  if key and key not in survey_keys and sum(counts.values()) >= 2
                  for name, _ in counts.most_common(5))


class Fetcher:
    def __init__(self, destination: Path, refresh=False):
        self.destination = destination
        destination.mkdir(parents=True, exist_ok=True)
        self.manifest_path = destination / "MANIFEST.json"
        self.manifest = json.loads(self.manifest_path.read_text()) if self.manifest_path.exists() else {"files": [], "unavailable": []}
        self.refresh = refresh
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def get(self, url, **params):
        for attempt in range(6):
            time.sleep(0.25)
            try:
                response = self.session.get(url, params=params, timeout=120)
                if response.status_code in {429, 502, 503, 504}:
                    delay = response.headers.get("Retry-After", "")
                    time.sleep(float(delay) if delay.isdigit() else min(60, 2 ** (attempt + 1)))
                    continue
                response.raise_for_status()
                return response
            except (requests.Timeout, requests.ConnectionError):
                if attempt == 5:
                    raise
                time.sleep(2 ** attempt)
        raise RuntimeError(f"Source unavailable after retries: {url}")

    def json(self, url, **params):
        data = self.get(url, **params).json()
        if isinstance(data, dict) and "error" in data:
            raise RuntimeError(f"Public API returned error: {data['error'].get('code', 'unknown')}")
        return data

    def so_tags(self, terms):
        """Established Stack Overflow tags (+ their synonyms) matching gap vocabulary terms."""
        filename = "stackoverflow_tags.json"
        if self.cached(filename):
            return
        from urllib.parse import quote
        candidates = {}
        for term in terms:
            for variant in tag_variants(term):
                candidates.setdefault(variant, term)
        names, found = sorted(candidates), {}
        for offset in range(0, len(names), 20):
            batch = ";".join(quote(n, safe=".-") for n in names[offset:offset + 20])
            for item in self.json(f"{SE_API}/tags/{batch}/info", site="stackoverflow", pagesize=100).get("items", []):
                found[item["name"]] = item["count"]
            time.sleep(0.5)
        accepted = {}
        for tag, count in found.items():
            term = candidates.get(tag)
            if term and count >= MIN_TAG_COUNT and count > accepted.get(term, ("", 0))[1]:
                accepted[term] = (tag, count)
        masters, synonyms = sorted({t for t, _ in accepted.values()}), {}
        for offset in range(0, len(masters), 20):
            batch = ";".join(quote(n, safe=".-") for n in masters[offset:offset + 20])
            for item in self.json(f"{SE_API}/tags/{batch}/synonyms", site="stackoverflow", pagesize=100).get("items", []):
                synonyms.setdefault(item["to_tag"], []).append(item["from_tag"])
            time.sleep(0.5)
        records = [{"tag": tag, "count": count, "display": term, "synonyms": sorted(synonyms.get(tag, []))}
                   for term, (tag, count) in sorted(accepted.items())]
        self.save(filename, {"min_count": MIN_TAG_COUNT, "records": records,
                             "note": "display = spelling of the term in the synthetic label vocabulary that matched the tag"},
                  url=f"{SE_API}/tags/{{tags}}/info ; {SE_API}/tags/{{tags}}/synonyms", version=datetime.now(timezone.utc).date().isoformat(),
                  licence="CC BY-SA 4.0", attribution="Stack Overflow tags, Stack Exchange, Inc. and contributors", prefix="stackoverflow-tags")

    def cached(self, filename):
        path = self.destination / filename
        entry = next((e for e in self.manifest["files"] if e["file"] == filename), None)
        return (not self.refresh and path.exists() and entry is not None
                and hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"])

    def save(self, filename, content, *, url, version, licence, attribution, prefix, **extra):
        raw = content if isinstance(content, bytes) else (json.dumps(content, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
        (self.destination / filename).write_bytes(raw)
        entry = dict(file=filename, url=url, retrieved=datetime.now(timezone.utc).date().isoformat(),
                     version=version, sha256=hashlib.sha256(raw).hexdigest(), licence=licence,
                     attribution=attribution, prefix=prefix, **extra)
        self.manifest["files"] = [e for e in self.manifest["files"] if e["file"] != filename] + [entry]
        self.manifest["files"].sort(key=lambda e: e["file"])
        self.manifest_path.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=2) + "\n")
        print(f"Saved {filename}", flush=True)

    def sparql(self, query):
        result = self.json(SPARQL, query=query, format="json")
        if "results" not in result:
            raise ValueError("Unexpected SPARQL response")
        return result

    def class_labels(self):
        filename = "wikidata_classes.json"
        roots = sorted(set(TECH_CLASSES) | {"Q3918", "Q38723", "Q189004", "Q1336920", "Q322563", "Q2696153", "Q4671277"})
        if self.cached(filename):
            old = json.loads((self.destination / filename).read_text())
            if set(roots) <= {r["item"]["value"].rsplit("/", 1)[-1] for r in old["results"]["results"]["bindings"]}:
                return
        query = 'SELECT ?item ?itemLabel WHERE { VALUES ?item { ' + ' '.join('wd:' + q for q in roots) + ' } SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }'
        result = self.sparql(query)
        if len(result["results"]["bindings"]) != len(roots):
            raise ValueError("Incomplete Wikidata class label verification")
        self.save(filename, {"query": query, "results": result}, url=SPARQL,
                  version="SPARQL class labels", licence="CC0 1.0", attribution="Wikidata contributors", prefix="wikidata")

    def wikidata(self, names, *, extend=False):
        filename = "wikidata_entities.json"
        path = self.destination / filename
        entry = next((e for e in self.manifest["files"] if e["file"] == filename), {})
        verified = path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == entry.get("sha256")
        previous = json.loads(path.read_text()) if verified else {}
        if (extend or not self.refresh) and previous.get("extension_version" if extend else "selection_version") == (7 if extend else SELECTION_VERSION):
            return
        candidates, gap_matches = {}, {}
        survey_matches = dict(previous.get("survey_matches", {})) if extend else {}
        gap_ids = set(previous.get("gap_fill_ids", [])) if extend else set()
        # Wikidata moved many software names/aliases to language-neutral `mul`.
        # Hydrate the old cache before searching, pinning fallback labels in the
        # same revision response as claims, rather than guessing missing names.
        if previous and previous.get("selection_version") != SELECTION_VERSION:
            qids = sorted(previous.get("entities", {}))
            for offset in range(0, len(qids), 50):
                response = self.json(WD_API, action="wbgetentities", ids="|".join(qids[offset:offset + 50]),
                                     props="info|labels|aliases|claims|sitelinks", languages="en|vi|mul", languagefallback=1, format="json")
                previous["entities"].update(response["entities"])
        known, search_cache = {}, {}
        for qid, entity in previous.get("entities", {}).items():
            for value in list(entity.get("labels", {}).values()) + [a for group in entity.get("aliases", {}).values() for a in group]:
                known.setdefault(value["value"].casefold(), set()).add(qid)
        # Sitelinks disambiguate common words whose technology entity is not in
        # the first five search hits. Only public article titles are queried.
        title_candidates = {}
        public_query = 'SELECT DISTINCT ?item ?label WHERE { VALUES ?label { ' + ' '.join(json.dumps(n) + '@' + lang for n in PUBLIC_TECH_QUERIES for lang in ("en", "mul")) + ' } { ?item rdfs:label ?label } UNION { ?item skos:altLabel ?label } ?item (wdt:P31/wdt:P279*|wdt:P279*) ?root . VALUES ?root { ' + ' '.join('wd:' + q for q in TECH_CLASSES) + ' } FILTER NOT EXISTS { ?item wdt:P31/wdt:P279* wd:Q7889 } }'
        for row in self.sparql(public_query)["results"]["bindings"]:
            name = row.get("label", {}).get("value")
            if name in PUBLIC_TECH_QUERIES:
                title_candidates.setdefault(name, set()).add(row["item"]["value"].rsplit("/", 1)[-1])
        prompts = [n for n, _ in names if n in PUBLIC_TECH_QUERIES]
        for offset in range(0, len(prompts), 15):
            titles = {variant: name for name in prompts[offset:offset + 15]
                      for variant in (name, name + " (software)", name + " (software company)", name + " (Python distribution)")}
            query = 'SELECT ?item ?title WHERE { VALUES ?title { ' + ' '.join(json.dumps(t) + '@en' for t in titles) + ' } ?article schema:name ?title; schema:isPartOf <https://en.wikipedia.org/>; schema:about ?item . }'
            for row in self.sparql(query)["results"]["bindings"]:
                name = titles.get(row.get("title", {}).get("value"))
                if name:
                    title_candidates.setdefault(name, set()).add(row["item"]["value"].rsplit("/", 1)[-1])
        # Search results are ephemeral; only accepted public entities are saved.
        for index, (name, is_survey) in enumerate(names):
            for variant in search_variants(name):
                ids = None if extend and name in PUBLIC_TECH_QUERIES else known.get(variant.casefold())
                if ids is None:
                    if variant.casefold() not in search_cache:
                        result = self.json(WD_API, action="wbsearchentities", search=variant, language="en", limit=5, format="json")
                        search_cache[variant.casefold()] = {item["id"] for item in result.get("search", [])}
                    ids = search_cache[variant.casefold()]
                for qid in ids:
                    candidates.setdefault(qid, []).append((variant, is_survey))
            for qid in title_candidates.get(name, set()):
                candidates.setdefault(qid, []).append((name, is_survey))
            if index % 100 == 0:
                print(f"Wikidata search {index + 1}/{len(names)}", flush=True)
        accepted = dict(previous.get("entities", {})) if extend else {}
        evidence = list(previous.get("class_evidence", [])) if extend else []
        qids = sorted(candidates)
        for offset in range(0, len(qids), 40):
            batch = qids[offset:offset + 40]
            query = "SELECT DISTINCT ?item ?root WHERE { hint:Query hint:optimizer \"None\" . VALUES ?item { " + " ".join("wd:" + q for q in batch) + " } VALUES ?root { " + " ".join("wd:" + q for q in TECH_CLASSES) + " } ?item (wdt:P31/wdt:P279*|wdt:P279*) ?root . FILTER(?root != wd:Q65938634 || EXISTS { ?item wdt:P1269 wd:Q950250 }) }"
            evidence.extend(self.sparql(query)["results"]["bindings"])
        roots = {}
        for row in evidence:
            roots.setdefault(row["item"]["value"].rsplit("/", 1)[-1], set()).add(row["root"]["value"].rsplit("/", 1)[-1])
        qualified = sorted(q for q in roots if q in candidates)
        for offset in range(0, len(qualified), 50):
            data = self.json(WD_API, action="wbgetentities", ids="|".join(qualified[offset:offset + 50]),
                             props="info|labels|aliases|claims|sitelinks", languages="en|vi|mul", languagefallback=1, format="json")
            for qid, entity in data.get("entities", {}).items():
                public_names = [v["value"] for v in entity.get("labels", {}).values()]
                public_names += [a["value"] for values in entity.get("aliases", {}).values() for a in values]
                matches = [(n, survey) for n, survey in candidates[qid] if skill_key(n) in {skill_key(p) for p in public_names}]
                if not matches:
                    continue
                entity["claims"] = {p: v for p, v in entity.get("claims", {}).items() if p in {"P31", "P277", "P361", "P527", "P1813"}}
                entity["sitelinks_count"] = len(entity.pop("sitelinks", {}))
                entity["accepted_classes"] = sorted(roots[qid])
                accepted[qid] = entity
                for name, survey in matches:
                    if survey:
                        survey_matches.setdefault(name, []).append(qid)
                    else:
                        gap_matches.setdefault(name, []).append(qid)
        # Prefer the entity with most sitelinks if an exact public label is ambiguous.
        survey_matches = {n: ids if isinstance(ids, str) else max(ids, key=lambda q: (accepted[q]["sitelinks_count"], q)) for n, ids in survey_matches.items()}
        for name, ids in gap_matches.items():
            # A generic acronym must not select a low-notability related tool
            # when the public vocabulary has a better-supported exact concept.
            gap_ids.difference_update(ids)
            acronym = bool(re.fullmatch(r"[A-Z0-9+#.]{2,8}", name))
            def rank(qid):
                primary = bool(set(accepted[qid]["accepted_classes"]) & {"Q9143", "Q37045", "Q235557", "Q483639", "Q176165"})
                return (acronym and primary, accepted[qid]["sitelinks_count"], qid)
            gap_ids.add(max(ids, key=rank))
        # Generic software membership alone must not turn a game called Lumen
        # into the PHP framework requested by a technology mention.
        for qid, entity in list(accepted.items()):
            if any(c.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id") == "Q7889"
                   for c in entity.get("claims", {}).get("P31", [])):
                del accepted[qid]
                gap_ids.discard(qid)
        survey_matches = {n: q for n, q in survey_matches.items() if q in accepted}
        components = dict(previous.get("survey_components", {})) if extend else {}
        for name, survey in names:
            if survey and "/" in name:
                components[name] = sorted({survey_matches[v] for v in search_variants(name) if v != name and v in survey_matches})
        self.save(filename, {**({k: previous[k] for k in ("soft_skill_ids", "esco_matches", "soft_evidence", "soft_query", "soft_selection_version") if k in previous} if extend else {}),
                  "extension_version": 7 if extend else 0,
                  "selection_version": SELECTION_VERSION, "retrieved": datetime.now(timezone.utc).isoformat(), "entities": accepted,
                  "survey_matches": survey_matches, "gap_fill_ids": sorted(gap_ids),
                  "survey_components": components,
                  "public_selection_query": public_query,
                  "class_roots": TECH_CLASSES, "class_evidence": [r for r in evidence if r["item"]["value"].rsplit("/", 1)[-1] in accepted]},
                  url=WD_API, version="entity revisions: lastrevid", licence="CC0 1.0",
                  attribution="Wikidata contributors", prefix="wikidata")

    def finish_wikidata(self, filename):
        """Record exact revisions, including when upgrading an older cached snapshot."""
        path = self.destination / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        revisions = {qid: entity.get("lastrevid") for qid, entity in data["entities"].items()}
        entry = next((e for e in self.manifest["files"] if e["file"] == filename), {})
        if data.get("snapshot_format") == 2 and entry.get("revision") == revisions:
            return
        qids = sorted(q for q, entity in data["entities"].items() if "lastrevid" not in entity)
        for offset in range(0, len(qids), 50):
            # Pin required content and its revision in the SAME API response.
            props = "info|labels|aliases|claims" + ("|sitelinks" if filename == "wikidata_entities.json" else "")
            response = self.json(WD_API, action="wbgetentities", ids="|".join(qids[offset:offset + 50]), props=props, languages="en|vi", format="json")
            for qid, entity in response["entities"].items():
                old = data["entities"][qid]
                allowed = {"P31", "P277", "P361", "P527", "P1813"} if filename == "wikidata_entities.json" else {"P1813"}
                entity["claims"] = {p: v for p, v in entity.get("claims", {}).items() if p in allowed}
                if filename == "wikidata_entities.json":
                    entity["sitelinks_count"] = len(entity.pop("sitelinks", {}))
                    entity["accepted_classes"] = old["accepted_classes"]
                data["entities"][qid] = entity
        if "class_evidence" in data:
            data["class_evidence"] = [r for r in data["class_evidence"] if r["item"]["value"].rsplit("/", 1)[-1] in data["entities"]]
        data["snapshot_format"] = 2
        data["retrieved"] = datetime.now(timezone.utc).isoformat()
        self.save(filename, data, url=WD_API if filename == "wikidata_entities.json" else SPARQL,
                  version="lastrevid recorded per entity", licence="CC0 1.0",
                  attribution="Wikidata contributors", prefix="wikidata",
                   revision={qid: entity["lastrevid"] for qid, entity in data["entities"].items()})

    def soft_skills(self):
        path = self.destination / "wikidata_entities.json"
        data = json.loads(path.read_text())
        if data.get("soft_selection_version") == 5:
            return
        technical = set(data.get("gap_fill_ids", [])) | set(data.get("survey_matches", {}).values())
        for qid in data.get("soft_skill_ids", []):
            if qid not in technical:
                data["entities"].pop(qid, None)
        # Exact English concept labels, not arbitrary top search hits (films etc.).
        query = 'SELECT ?item ?label WHERE { VALUES ?label { ' + ' '.join(json.dumps(s) + '@en' for s in SOFT_QUERIES) + ' } ?item rdfs:label ?label . FILTER NOT EXISTS { ?item wdt:P31/wdt:P279* wd:Q11424 } }'
        evidence = self.sparql(query)
        qids = sorted({r["item"]["value"].rsplit("/", 1)[-1] for r in evidence["results"]["bindings"]})
        response = self.json(WD_API, action="wbgetentities", ids="|".join(qids), props="info|labels|aliases|claims|sitelinks", languages="en|vi", format="json")
        winners = {}
        for qid, entity in response["entities"].items():
            label = entity.get("labels", {}).get("en", {}).get("value", "")
            old = winners.get(label)
            if old is None or len(entity.get("sitelinks", {})) > len(response["entities"][old].get("sitelinks", {})):
                winners[label] = qid
        records = json.loads((self.destination / "esco_transversal.json").read_text())["records"]
        def key(s):
            # Compare nominal/verb forms from the two public vocabularies,
            # never manufacture aliases from the input prompts.
            tokens = []
            for token in re.findall(r"[a-z]+", s.casefold()):
                if len(token) > 4 and token.endswith("ing"):
                    token = token[:-3]
                elif len(token) > 6 and token.endswith("ment"):
                    token = token[:-4]
                elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
                    token = token[:-1]
                tokens.append(token.removesuffix("e"))
            return "".join(sorted(tokens))
        matches, soft_ids = {}, []
        for qid, entity in response["entities"].items():
            if qid not in winners.values():
                continue
            surfaces = [v["value"] for v in entity.get("labels", {}).values()] + [a["value"] for group in entity.get("aliases", {}).values() for a in group]
            owners = []
            for record in records:
                if record.get("className") != "Skill":
                    continue
                if any(link["uri"].endswith("/skills-hierarchy") for link in record.get("_links", {}).get("isInScheme", [])):
                    continue
                public = [record.get("preferredLabel", {}).get("en", ""), *record.get("alternativeLabel", {}).get("en", [])]
                if {key(s) for s in surfaces if key(s)} & {key(s) for s in public if key(s)}:
                    owners.append(record["uri"])
            if len(owners) == 1:
                matches[qid] = owners[0]
            entity["claims"] = {p: c for p, c in entity.get("claims", {}).items() if p in {"P31", "P1813"}}
            entity["sitelinks_count"] = len(entity.pop("sitelinks", {}))
            entity["accepted_classes"] = []
            data["entities"][qid] = entity
            soft_ids.append(qid)
        data.update(soft_skill_ids=soft_ids, esco_matches=matches, soft_evidence=evidence,
                    soft_query=query, soft_selection_version=5)
        self.save("wikidata_entities.json", data, url=WD_API, version="entity revisions: lastrevid", licence="CC0 1.0", attribution="Wikidata contributors", prefix="wikidata")

    def esco_tree(self, filename, roots, kind):
        entry = next((e for e in self.manifest["files"] if e["file"] == filename), {})
        if self.cached(filename) and entry.get("version") == ESCO_VERSION:
            data = json.loads((self.destination / filename).read_text())
            if data.get("snapshot_format") != 3:
                data["records"] = [compact_esco(r) for r in data["records"]]
                data["snapshot_format"] = 3
                self.save(filename, data, url=ESCO, version=ESCO_VERSION, licence="CC BY 4.0",
                          attribution="© European Union, ESCO", prefix="esco")
            return
        pending, seen, records = list(roots), set(), []
        while pending:
            batch = []
            while pending and len(batch) < 20:
                uri = pending.pop(0)
                if uri not in seen:
                    seen.add(uri)
                    batch.append(uri)
            if not batch:
                continue
            response = self.json(ESCO + "/resource/" + kind, uris=",".join(batch), language="en", selectedVersion=ESCO_VERSION)
            embedded = response.get("_embedded", {})
            if set(batch) - set(embedded):
                raise ValueError(f"Incomplete ESCO bulk response: {filename}")
            for uri in batch:
                data = embedded[uri]
                records.append(compact_esco(data))
                # A member skill's semantic narrowerSkill links point to
                # occupation-specific skills, NOT children of the T taxonomy.
                # Stop at taxonomy members rather than crawling all ESCO skills.
                schemes = {s["uri"] for s in data.get("_links", {}).get("isInScheme", [])}
                if kind == "skill" and "http://data.europa.eu/esco/concept-scheme/member-skills" in schemes:
                    continue
                for relation in ("narrowerConcept", "narrowerSkill", "narrowerOccupation"):
                    children = data.get("_links", {}).get(relation, [])
                    if isinstance(children, dict):
                        children = [children]
                    pending.extend(c["uri"] for c in children)
            print(f"ESCO {kind}: {len(records)} public concepts", flush=True)
        if len(records) <= len(roots):
            raise ValueError(f"Empty ESCO subtree: {filename}")
        self.save(filename, {"snapshot_format": 3, "selectedVersion": ESCO_VERSION, "roots": roots, "kind": kind, "records": records},
                  url=ESCO, version=ESCO_VERSION, licence="CC BY 4.0", attribution="© European Union, ESCO", prefix="esco")


def fetch_sources(destination=ROOT / "sources", refresh=False):
    fetcher = Fetcher(Path(destination), refresh)
    fetcher.class_labels()
    # FPT Polytechnic has no discoverable Wikidata item. Use the institution's
    # own published title as a narrow, explicitly attributed fallback.
    if not fetcher.cached("official_vn_colleges.json"):
        url = "https://caodang.fpt.edu.vn/"
        response = fetcher.get(url)
        title = re.search(r"<title[^>]*>(.*?)</title>", response.text, re.I | re.S)
        if title is None:
            raise ValueError("Official college page has no published title")
        published_title = html.unescape(re.sub(r"\s+", " ", title.group(1))).strip()
        name = re.sub(r"^Trang chủ\s*[-–—|]\s*", "", published_title, flags=re.I)
        if not re.match(r"^(Trường\s+)?Cao\s+đẳng\s+\S", name, re.I):
            raise ValueError("Official college title changed: review extraction")
        fetcher.save("official_vn_colleges.json", {"records": [{"url": url, "published_title": published_title, "name": name}]},
                     url=url, version=response.headers.get("Last-Modified", datetime.now(timezone.utc).date().isoformat()),
                     licence="Factual names only; website copyright retained", attribution="FPT Polytechnic, official institution website", prefix="institution")
    names = set()
    for year in (2024, 2025, 2026):
        filename = f"stackoverflow_{year}_technology.json"
        url = f"https://raw.githubusercontent.com/StackExchange/Survey/main/packages/archive/{year}/json/technology.json"
        if not fetcher.cached(filename):
            try:
                response = fetcher.get(url)
            except requests.HTTPError as error:
                if error.response.status_code != 404:
                    raise
                fetcher.manifest["files"] = [e for e in fetcher.manifest["files"] if e["file"] != filename]
                fetcher.manifest["unavailable"] = [e for e in fetcher.manifest["unavailable"] if e["url"] != url]
                fetcher.manifest["unavailable"].append({"url": url, "year": year, "status": 404, "retrieved": datetime.now(timezone.utc).date().isoformat()})
                fetcher.manifest_path.write_text(json.dumps(fetcher.manifest, indent=2) + "\n")
                continue
            fetcher.manifest["unavailable"] = [e for e in fetcher.manifest["unavailable"] if e["url"] != url]
            fetcher.save(filename, response.content, url=url, version=str(year),
                         licence="ODbL 1.0 / DbCL 1.0", attribution=f"Stack Overflow Developer Survey {year}, Stack Exchange, Inc.", prefix=f"stackoverflow-{year}")
        names.update(n for n, _, _ in survey_options(json.loads((Path(destination) / filename).read_text())))
    if not fetcher.cached("languages.yml"):
        revision = fetcher.json("https://api.github.com/repos/github-linguist/linguist/commits/main")["sha"]
        url = f"https://raw.githubusercontent.com/github-linguist/linguist/{revision}/lib/linguist/languages.yml"
        fetcher.save("languages.yml", fetcher.get(url).content, url=url, version=revision,
                     licence="MIT", attribution="GitHub, Inc. and Linguist contributors", prefix="linguist")
    if not fetcher.cached("linguist_LICENSE"):
        revision = next(e["version"] for e in fetcher.manifest["files"] if e["file"] == "languages.yml")
        url = f"https://raw.githubusercontent.com/github-linguist/linguist/{revision}/LICENSE"
        fetcher.save("linguist_LICENSE", fetcher.get(url).content, url=url, version=revision,
                     licence="MIT", attribution="GitHub, Inc. and Linguist contributors", prefix="linguist")
    university_file = ROOT / "seed/vn_universities.csv"
    if not fetcher.cached("vn_universities.csv"):
        original = university_file if university_file.exists() else Path(destination) / "vn_universities.csv"
        fetcher.save("vn_universities.csv", original.read_bytes(),
                     url="https://vi.wikipedia.org/w/index.php?title=Danh_sách_trường_đại_học,_học_viện_và_cao_đẳng_tại_Việt_Nam&oldid=75654510",
                     version="75654510", licence="CC BY-SA 4.0", attribution="Wikipedia tiếng Việt contributors", prefix="wikipedia")
    fetcher.esco_tree("esco_transversal.json", ["http://data.europa.eu/esco/skill/04a13491-b58c-4d33-8b59-8fad0d55fe9e"], "skill")
    fetcher.esco_tree("esco_occupations.json", ["http://data.europa.eu/esco/isco/C25", "http://data.europa.eu/esco/isco/C35"], "occupation")
    school_path = Path(destination) / "wikidata_vn_universities.json"
    if not fetcher.cached("wikidata_vn_universities.json") or json.loads(school_path.read_text()).get("selection_version") != 4:
        query = '''SELECT DISTINCT ?item WHERE {
          ?item wdt:P17 wd:Q881 . VALUES ?root { wd:Q3918 wd:Q38723 wd:Q189004 wd:Q1336920 wd:Q322563 wd:Q2696153 wd:Q4671277 }
          ?item wdt:P31/wdt:P279* ?root .
        }'''
        # Retrieve entities as well: label service alone returns aliases in one language.
        result = fetcher.sparql(query)
        qids = sorted({r["item"]["value"].rsplit("/", 1)[-1] for r in result["results"]["bindings"]})
        entities = {}
        for offset in range(0, len(qids), 50):
            response = fetcher.json(WD_API, action="wbgetentities", ids="|".join(qids[offset:offset + 50]), props="info|labels|aliases|claims|sitelinks", languages="en|vi", format="json")
            for qid, entity in response["entities"].items():
                entity["claims"] = {p: v for p, v in entity.get("claims", {}).items() if p == "P1813"}
                entity["sitelink_titles"] = [s["title"] for site, s in entity.pop("sitelinks", {}).items() if site in {"enwiki", "viwiki"}]
                entities[qid] = entity
        fetcher.save("wikidata_vn_universities.json", {"selection_version": 4, "query": query, "results": result, "entities": entities},
                     url=SPARQL, version="entity revisions: lastrevid", licence="CC0 1.0", attribution="Wikidata contributors", prefix="wikidata")
    vocabulary = synthetic_vocabulary(ROOT.parent)
    gaps = sorted(set(gap_vocabulary(vocabulary, names)) | set(PUBLIC_TECH_QUERIES))
    fetcher.wikidata([(n, True) for n in sorted(names)] + [(n, False) for n in gaps])
    extension = set(PUBLIC_TECH_QUERIES) | {n for n in gaps if vocabulary.get(n, 0) < 2}
    fetcher.wikidata([(n, False) for n in sorted(extension)], extend=True)
    fetcher.so_tags(gaps)
    fetcher.soft_skills()
    fetcher.finish_wikidata("wikidata_entities.json")
    fetcher.finish_wikidata("wikidata_vn_universities.json")
    return fetcher.manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    fetch_sources(refresh=args.refresh)


if __name__ == "__main__":
    main()
