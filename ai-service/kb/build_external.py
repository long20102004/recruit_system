"""Deterministic, offline KB builder: public snapshots only, never training labels."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re

from app.kb.keys import school_key, skill_key
from app.postprocess.text_match import normalize
from kb.fetch_sources import QUESTION_CATEGORIES, ROOT, TECH_CLASSES, survey_options
from kb.load import read_seed, validate

CATEGORIES = [
    "Programming Language", "Framework/Library", "Frontend", "Mobile", "Database",
    "Cloud", "DevOps/CI-CD", "Testing/QA", "Data/AI", "Business Analysis",
    "Design/UI-UX", "Security", "Tool/Platform", "Methodology/Concept", "Soft Skill", "Other",
]
# Safety policy, not vocabulary: never introduce aliases from this set.
AMBIGUOUS_ALIASES = {"cake", "coffee", "of", "on", "in", "and", "or", "as", "do", "no", "yes", "text", "all", "none"}
FIELDS = {
    "categories": ["id", "name", "source"],
    "skills": ["id", "name", "category", "source", "source_id"],
    "skill_aliases": ["alias_key", "skill_id", "surface", "source"],
    "skill_edges": ["src_id", "rel", "dst_id", "source"],
    "universities": ["id", "name", "source"],
    "university_aliases": ["university_id", "alias_key", "source"],
    "job_titles": ["id", "name", "alias_key", "source"],
}


def csv_rows(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def entity_surfaces(entity):
    surfaces = [v["value"] for lang, v in entity.get("labels", {}).items() if lang in {"en", "vi", "mul"}]
    surfaces += [a["value"] for lang, aliases in entity.get("aliases", {}).items() if lang in {"en", "vi", "mul"} for a in aliases]
    surfaces += entity.get("sitelink_titles", [])
    # Some public aliases combine the product name and its scoped npm import.
    for surface in list(surfaces):
        package = re.fullmatch(r"(.+?)\s+(@[\w.-]+/[\w.-]+)", surface)
        if package:
            surfaces.extend(package.groups())
    for claim in entity.get("claims", {}).get("P1813", []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        if isinstance(value, dict) and value.get("language") in {"en", "vi", ""} and value.get("text"):
            surfaces.append(value["text"])
    return sorted(set(surfaces))


def claim_ids(entity, prop):
    return [c["mainsnak"]["datavalue"]["value"]["id"]
            for c in entity.get("claims", {}).get(prop, [])
            if c.get("rank") != "deprecated" and isinstance(c.get("mainsnak", {}).get("datavalue", {}).get("value"), dict)
            and "id" in c["mainsnak"]["datavalue"]["value"]]


def entity_category(entity):
    classes = set(entity.get("accepted_classes", []))
    # Narrow classes precede the generic software superclass.
    for qid in [qid for qid in TECH_CLASSES if qid != "Q7397"] + ["Q7397"]:
        if qid in classes:
            return TECH_CLASSES.get(qid, "Other")
    return "Other"


def linguist_languages(path):
    """PyYAML if installed; restricted fallback handles only top-level names/aliases."""
    try:
        import yaml
    except ImportError:
        result, current, aliases = {}, None, False
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line[0].isspace() and not line.startswith("#") and line.endswith(":"):
                current = line[:-1].strip('"\'')
                result[current] = {"aliases": []}
                aliases = False
            elif current and line == "  aliases:":
                aliases = True
            elif current and aliases and line.startswith("  - "):
                result[current]["aliases"].append(line[4:].strip('"\''))
            elif line.startswith("  ") and not line.startswith("  - "):
                aliases = False
        return result
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def unambiguous(rows, key_field, owner_field):
    grouped = defaultdict(list)
    for row in rows:
        if row[key_field]:
            grouped[row[key_field]].append(row)
    result, collisions = [], 0
    for key, candidates in sorted(grouped.items()):
        if len({r[owner_field] for r in candidates}) != 1:
            collisions += 1
        else:
            result.append(min(candidates, key=lambda r: (r["source"], r.get("surface", ""))))
    return result, collisions


def acyclic_edges(candidates):
    """Sorted insertion rejects an edge if its destination can already reach its source.

    A union graph is used (stronger than the loader's per-relation check).
    """
    graph, result, dropped = defaultdict(set), [], 0
    seen = set()
    for row in sorted(candidates, key=lambda r: (r["src_id"], r["rel"], r["dst_id"], r["source"])):
        src, dst = row["src_id"], row["dst_id"]
        key = (src, row["rel"], dst)
        if key in seen:
            continue
        pending, visited = [dst], set()
        while pending:
            node = pending.pop()
            if node not in visited:
                visited.add(node)
                pending.extend(graph[node] - visited)
        if src in visited:
            dropped += 1
            continue
        graph[src].add(dst)
        seen.add(key)
        result.append(row)
    return result, dropped


def build_external(sources_dir=ROOT / "sources", out_dir=ROOT / "seed"):
    sources, output = Path(sources_dir), Path(out_dir)
    manifest = json.loads((sources / "MANIFEST.json").read_text(encoding="utf-8"))
    entries = {e["file"]: e for e in manifest["files"]}
    for filename, entry in entries.items():
        path = sources / filename
        if path.resolve().parent != sources.resolve():
            raise ValueError("Snapshot path outside sources directory")
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Snapshot checksum mismatch: {filename}")

    def document(filename):
        if filename not in entries:
            raise ValueError(f"Snapshot missing from manifest: {filename}")
        return json.loads((sources / filename).read_text(encoding="utf-8"))

    wd = document("wikidata_entities.json")
    entities = wd["entities"]
    survey_matches = wd.get("survey_matches", {})
    public_names = defaultdict(set)
    active_qids = (set(wd.get("gap_fill_ids", [])) | set(survey_matches.values())
                   | {q for ids in wd.get("survey_components", {}).values() for q in ids}
                   | set(wd.get("soft_skill_ids", [])))
    for qid, entity in entities.items():
        if qid not in active_qids:
            continue
        for surface in entity_surfaces(entity):
            public_names[skill_key(surface)].add(qid)

    def survey_entity(name):
        if name in survey_matches:
            return survey_matches[name]
        # Join only against already accepted public entities, never synthetic text.
        # Survey names such as "Amazon Web Services (AWS)" retain their full
        # canonical spelling while matching an explicitly published acronym.
        surfaces = [name]
        acronym = re.fullmatch(r"(.+) \(([A-Z0-9-]{2,})\)", name)
        if acronym:
            surfaces.extend(acronym.groups())
        candidates = set().union(*(public_names.get(skill_key(s), set()) for s in surfaces))
        return next(iter(candidates)) if len(candidates) == 1 else ""
    skills_by_key, aliases, qid_to_key = {}, [], {}
    for filename in sorted(entries, reverse=True):
        if not re.fullmatch(r"stackoverflow_\d{4}_technology.json", filename):
            continue
        prefix = entries[filename]["prefix"]
        for name, question, category in survey_options(document(filename)):
            qid = survey_entity(name)
            key = qid_to_key.get(qid, skill_key(name)) if qid else skill_key(name)
            if not key:
                continue
            entity = entities.get(qid, {})
            if question in {"Platform", "CloudPlat"}:
                # Without a qualified Wikidata entity, retain the survey's
                # cloud/platform classification rather than inventing a type.
                if entity:
                    category = "Cloud" if "Q483639" in entity.get("accepted_classes", []) else "Tool/Platform"
            source = f"{prefix}:{question}"
            skills_by_key.setdefault(key, {"name": name, "category": category, "source": source, "source_id": qid})
            aliases.append({"alias_key": skill_key(name), "owner": key, "surface": name, "source": source})
            acronym = re.fullmatch(r"(.+) \(([A-Z0-9-]{2,})\)", name)
            if acronym:
                for surface in acronym.groups():
                    aliases.append({"alias_key": skill_key(surface), "owner": key, "surface": surface, "source": source})
            if qid:
                qid_to_key[qid] = key
            # Combined survey options are not identities: HTML and CSS each
            # retain their own accepted public entity and canonical label.
            for component in wd.get("survey_components", {}).get(name, []):
                entity = entities.get(component, {})
                label = entity.get("labels", {}).get("en", {}).get("value")
                if not entity.get("accepted_classes") or not label:
                    continue
                entity_keys = {skill_key(x) for x in entity_surfaces(entity)}
                parts = [part.strip() for part in re.split(r"/", name) if skill_key(part) in entity_keys]
                # "Torch/PyTorch": prefer the part that is the entity's own label
                label = next((p for p in parts if skill_key(p) == skill_key(label)), parts[0] if parts else label)
                component_key = qid_to_key.get(component, skill_key(label))
                if component_key:
                    skills_by_key.setdefault(component_key, {
                        "name": label, "category": entity_category(entity),
                        "source": f"wikidata:{component}", "source_id": component,
                    })
                    qid_to_key[component] = component_key
    for qid in sorted(wd.get("gap_fill_ids", [])):
        entity = entities[qid]
        if not entity.get("accepted_classes") or not entity.get("labels", {}).get("en"):
            continue
        name = entity["labels"]["en"]["value"]
        key = qid_to_key.get(qid, skill_key(name))
        if not key:
            continue
        skills_by_key.setdefault(key, {"name": name, "category": entity_category(entity), "source": f"wikidata:{qid}", "source_id": qid})
        qid_to_key[qid] = key
    # Stack Overflow tags: established tags matching gap vocabulary the other sources lack
    # (Spring MVC, Lombok, AutoMapper...). Never override a key owned by another source.
    if "stackoverflow_tags.json" in entries:
        taken = set(skills_by_key) | set(public_names) | {a["alias_key"] for a in aliases}
        for record in document("stackoverflow_tags.json")["records"]:
            key, tag_key = skill_key(record["display"]), skill_key(record["tag"])
            if not key or key in taken or tag_key in taken:
                continue
            source = f"stackoverflow-tags:{record['tag']}"
            skills_by_key[key] = {"name": record["display"], "category": "Other", "source": source, "source_id": record["tag"]}
            for surface in [record["display"], record["tag"], record["tag"].replace("-", " "), *record["synonyms"]]:
                aliases.append({"alias_key": skill_key(surface), "owner": key, "surface": surface, "source": source})
            taken |= {key, tag_key}
    esco_skills = document("esco_transversal.json")
    esco_keys = {}
    for record in esco_skills["records"]:
        if record["uri"] in esco_skills["roots"]:
            continue
        # Hierarchy/group concepts are not individual skills.
        if record.get("className") != "Skill":
            continue
        schemes = {s["uri"] for s in record.get("_links", {}).get("isInScheme", [])}
        if "http://data.europa.eu/esco/concept-scheme/skills-hierarchy" in schemes:
            continue
        name = record.get("preferredLabel", {}).get("en", record.get("title", ""))
        key, source = skill_key(name), "esco:" + record["uri"]
        if not key:
            continue
        skills_by_key.setdefault(key, {"name": name, "category": "Soft Skill", "source": source, "source_id": record["uri"]})
        esco_keys[record["uri"]] = key
        for surface in [name, *record.get("alternativeLabel", record.get("altLabels", {})).get("en", [])]:
            aliases.append({"alias_key": skill_key(surface), "owner": key, "surface": surface, "source": source})
    for qid in sorted(wd.get("soft_skill_ids", [])):
        entity = entities.get(qid, {})
        name = entity.get("labels", {}).get("en", {}).get("value")
        if not name:
            continue
        matched_key = esco_keys.get(wd.get("esco_matches", {}).get(qid))
        old_key = qid_to_key.get(qid)
        key = matched_key or old_key or skill_key(name)
        if not key:
            continue
        if matched_key and old_key and old_key != key:
            # Only retire a row owned by this entity, not an unrelated name
            # collision. Move aliases and all entity references with it.
            if skills_by_key[old_key]["source_id"] == qid:
                del skills_by_key[old_key]
                for alias in aliases:
                    if alias["owner"] == old_key:
                        alias["owner"] = key
                for other_qid in qid_to_key:
                    if qid_to_key[other_qid] == old_key:
                        qid_to_key[other_qid] = key
        if not matched_key and key in skills_by_key and skills_by_key[key]["category"] != "Soft Skill":
            if skills_by_key[key]["source_id"] != qid:
                continue
            skills_by_key[key]["category"] = "Soft Skill"
        skills_by_key.setdefault(key, {"name": name, "category": "Soft Skill",
                                      "source": f"wikidata:{qid}", "source_id": qid})
        qid_to_key[qid] = key
    for row in skills_by_key.values():
        if row["source"].startswith("wikidata:") and row["name"][:1].islower():
            row["name"] = row["name"][0].upper() + row["name"][1:]
    ordered = sorted(skills_by_key, key=lambda k: (skills_by_key[k]["name"].casefold(), k))
    ids = {key: index for index, key in enumerate(ordered, 1)}
    skills = [dict(id=ids[key], **skills_by_key[key]) for key in ordered]
    for qid, key in sorted(qid_to_key.items()):
        for surface in entity_surfaces(entities[qid]):
            if surface.casefold() not in AMBIGUOUS_ALIASES:
                aliases.append({"alias_key": skill_key(surface), "owner": key, "surface": surface, "source": f"wikidata:{qid}"})
    language_path = sources / "languages.yml"
    if "languages.yml" not in entries:
        raise ValueError("Linguist snapshot missing from manifest")
    for name, record in linguist_languages(language_path).items():
        key = skill_key(name)
        if key in ids and skills_by_key[key]["category"] == "Programming Language":
            for surface in record.get("aliases", []):
                if surface.casefold() not in AMBIGUOUS_ALIASES:
                    aliases.append({"alias_key": skill_key(surface), "owner": key, "surface": surface, "source": f"linguist:{name}"})
    aliases, alias_collisions = unambiguous(aliases, "alias_key", "owner")
    aliases = [{"skill_id": ids[r["owner"]], **{k: v for k, v in r.items() if k != "owner"}} for r in aliases]
    edge_candidates = []
    for qid, key in sorted(qid_to_key.items()):
        entity = entities[qid]
        framework = bool(set(entity.get("accepted_classes", [])) & {"Q271680", "Q188860", "Q1330336"})
        for prop, relation in (("P277", "REQUIRES"), ("P361", "PART_OF"), ("P527", "PART_OF")):
            if prop == "P277" and not framework:
                continue
            for target in claim_ids(entity, prop):
                if target not in qid_to_key:
                    continue
                src, dst = ids[key], ids[qid_to_key[target]]
                if prop == "P527":
                    src, dst = dst, src
                edge_candidates.append(dict(src_id=src, rel=relation, dst_id=dst, source=f"wikidata:{qid}:{prop}"))
    edges, cycle_drops = acyclic_edges(edge_candidates)

    # Wikipedia names take priority; query-backed Wikidata adds missing schools.
    if "vn_universities.csv" not in entries:
        raise ValueError("Wikipedia snapshot missing from manifest")
    wikipedia = csv_rows(sources / "vn_universities.csv")
    names = sorted({r["name_vi"].strip() for r in wikipedia if r.get("name_vi", "").strip()})
    university_ids = {name: index for index, name in enumerate(names, 1)}
    parent_name_keys = {school_key(name) for name in names}
    wiki_source = "wikipedia:vi:" + entries["vn_universities.csv"]["version"]
    universities = [dict(id=university_ids[name], name=name, source=wiki_source) for name in names]
    uni_aliases, reference = [], defaultdict(set)
    for row in wikipedia:
        uid = university_ids.get(row.get("name_vi", "").strip())
        if uid is None:
            continue
        for col in ("name_vi", "name_en", "abbreviation"):
            surface = row.get(col, "").strip()
            if surface and surface not in {"-", "—"}:
                key = school_key(surface)
                # Identity joins use full official vi/en names, never a bare
                # abbreviation that can also name a parent/member institution.
                if col in {"name_vi", "name_en"}:
                    reference[key].add(uid)
                    if "," in surface and row.get("group") and school_key(surface.rsplit(",", 1)[-1]) == school_key(row["group"]):
                        reference[school_key(surface.split(",", 1)[0])].add(uid)
                uni_aliases.append(dict(university_id=uid, alias_key=key, source=wiki_source))
    university_snapshot = document("wikidata_vn_universities.json")
    for qid, entity in sorted(university_snapshot["entities"].items()):
        surfaces = entity_surfaces(entity)
        labels = [v["value"] for lang, v in entity.get("labels", {}).items() if lang in {"en", "vi"}]
        labels += entity.get("sitelink_titles", [])
        labels += [s.rsplit(",", 1)[0] for s in labels
                   if "," in s and school_key(s.rsplit(",", 1)[-1]) in parent_name_keys]
        owners = set().union(*(reference.get(school_key(s), set()) for s in labels))
        if len(owners) > 1:
            continue
        if owners:
            uid = next(iter(owners))
        elif university_snapshot.get("query"):
            name = next((entity.get("labels", {}).get(lang, {}).get("value")
                         for lang in ("vi", "en") if entity.get("labels", {}).get(lang, {}).get("value")), "")
            if not name or not school_key(name):
                continue
            uid = len(universities) + 1
            universities.append(dict(id=uid, name=name, source=f"wikidata:{qid}"))
        else:
            continue
        for label in labels:
            reference[school_key(label)].add(uid)
        for surface in surfaces:
            uni_aliases.append(dict(university_id=uid, alias_key=school_key(surface), source=f"wikidata:{qid}"))
    # Spelling variants of the same published names (no new names): "Ho Chi Minh City" <-> "HCMC" / "TP HCM",
    # "Cao đẳng X" <-> "X College".
    variants = []
    for row in uni_aliases:
        key = row["alias_key"]
        for long, short in (("ho chi minh city", "hcmc"), ("thanh pho ho chi minh", "tp hcm"), ("thanh pho ho chi minh", "tphcm")):
            if long in key:
                variants.append(dict(row, alias_key=" ".join(key.replace(long, short).split())))
        college = re.fullmatch(r"(?:truong )?cao dang (.+)", key)
        if college:
            variants.append(dict(row, alias_key=college.group(1) + " college"))
    uni_aliases += variants
    blocklist = {school_key(r["alias"]) for r in csv_rows(output / "university_alias_blocklist.csv")}
    if "official_vn_colleges.json" in entries:
        for record in document("official_vn_colleges.json")["records"]:
            name = record["name"]
            source = "institution:" + record["url"].split("/")[2]
            uid = next((r["id"] for r in universities if school_key(r["name"]) == school_key(name)), len(universities) + 1)
            if uid > len(universities):
                universities.append(dict(id=uid, name=name, source=source))
            short = re.sub(r"^(Trường\s+)?Cao\s+đẳng\s+", "", name, flags=re.I)
            for surface in (name, short):
                uni_aliases.append(dict(university_id=uid, alias_key=school_key(surface), source=source))
    uni_aliases = [r for r in uni_aliases if r["alias_key"] not in blocklist]
    uni_aliases, school_collisions = unambiguous(uni_aliases, "alias_key", "university_id")

    job_candidates = []
    occupations = document("esco_occupations.json")
    for record in occupations["records"]:
        if "/occupation/" not in record["uri"]:
            continue
        name = record.get("preferredLabel", {}).get("en", record.get("title", ""))
        for surface in [name, *record.get("alternativeLabel", record.get("altLabels", {})).get("en", [])]:
            if surface.strip():
                job_candidates.append(dict(name=surface.strip(), alias_key=normalize(surface), source="esco:" + record["uri"], owner=record["uri"]))
    job_candidates, job_collisions = unambiguous(job_candidates, "alias_key", "owner")
    job_titles = [dict(id=index, **{k: v for k, v in row.items() if k != "owner"}) for index, row in enumerate(job_candidates, 1)]
    if not skills:
        raise ValueError("No skills in public snapshots")
    taxonomy_source = next(r["source"] for r in skills if r["source"].startswith("stackoverflow-"))
    categories = [dict(id=index, name=name,
                       source=next((s["source"] for s in skills if s["category"] == name), taxonomy_source))
                  for index, name in enumerate(CATEGORIES, 1)]
    tables = dict(categories=categories, skills=skills, skill_aliases=aliases, skill_edges=edges,
                  universities=universities, university_aliases=uni_aliases, job_titles=job_titles)
    errors = validate(tables)
    if errors:
        raise ValueError("Invalid generated seed: " + "; ".join(errors))
    prefixes = {e["prefix"] for e in entries.values()}
    for rows in tables.values():
        for row in rows:
            if row["source"].split(":", 1)[0] not in prefixes:
                raise ValueError("Unknown provenance prefix")
    output.mkdir(parents=True, exist_ok=True)
    for table, rows in tables.items():
        with (output / f"{table}.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS[table], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    summary = {table: len(rows) for table, rows in tables.items()}
    summary.update(alias_collisions=alias_collisions, school_alias_collisions=school_collisions,
                   job_alias_collisions=job_collisions, cycle_edges_dropped=cycle_drops)
    write_sources(output, manifest, tables, summary)
    return summary


def write_sources(output, manifest, tables, summary):
    licences = {
        "ODbL 1.0 / DbCL 1.0": "https://opendatacommons.org/licenses/odbl/1-0/ ; https://opendatacommons.org/licenses/dbcl/1-0/",
        "MIT": "https://opensource.org/license/mit",
        "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
        "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
        "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    }
    lines = ["# Nguồn dữ liệu Knowledge Base", "",
             "Seed được dựng offline bằng `python -m kb.build_external`, chỉ từ snapshot trong `kb/sources/`. "
             "SHA-256 được kiểm tra trước khi dựng; MANIFEST.json ghi URL, phiên bản, ngày truy cập và giấy phép. "
             "Mỗi dòng mang `source`; phần trước dấu `:` khớp `prefix` trong manifest. "
             "Số liệu bên dưới đếm nguồn trực tiếp của từng dòng (không đếm lặp các nguồn bổ trợ).", ""]
    explanations = {
        "stackoverflow": "Stack Overflow Developer Survey — lựa chọn công nghệ, tên chuẩn và câu hỏi phân nhóm; dùng cho skills, skill_aliases và ánh xạ categories.",
        "stackoverflow-tags": "Stack Overflow tags (nội dung người dùng, CC BY-SA 4.0) — chỉ các tag đã phổ biến (≥ 500 câu hỏi) khớp từ vựng kỹ năng của CV tổng hợp mà khảo sát/Wikidata không có (ví dụ Spring MVC, Lombok, AutoMapper); tag và tag đồng nghĩa làm alias; nhóm để Other.",
        "linguist": "GitHub Linguist — alias của ngôn ngữ đã có trong skills; dùng cho skill_aliases, không thêm ngôn ngữ ngoài phạm vi khảo sát/gap-fill.",
        "wikidata": "Wikidata, cộng đồng biên tập viên và Wikimedia Foundation — nhãn/alias en, vi, P1813, lớp P31/P279*, P277/P361/P527; dùng cho skills gap-fill, kỹ năng mềm, skill_aliases, skill_edges, universities và university_aliases.",
        "esco": "ESCO, European Commission / European Union (https://esco.ec.europa.eu) — kỹ năng transversal và nhãn nghề ICT thuộc ISCO 25, 35; snapshot compact giữ nhãn, URI, loại và liên kết cần thiết từ API, không phải bản sao nguyên response; dùng cho skills, skill_aliases và job_titles.",
        "wikipedia": "Wikipedia tiếng Việt, cộng đồng biên tập viên và Wikimedia Foundation — bảng đại học/học viện và trường thành viên; tên chính thức tiếng Việt và tên khác trong bản trích dẫn; dùng cho universities và university_aliases. Bản trích dẫn theo CC BY-SA 4.0.",
        "institution": "Trang chính thức của cơ sở đào tạo — chỉ trích tên trường từ title công khai và tên ngắn bằng bỏ tiền tố Cao đẳng; không sao chép nội dung bài, không khẳng định website có giấy phép mở. Fallback hẹp cho FPT Polytechnic khi không tìm thấy item Wikidata.",
    }
    for entry in manifest["files"]:
        family = entry["prefix"].split("-", 1)[0]
        lines += [f"## {entry['file']}", "", explanations.get(entry["prefix"], explanations.get(family, "")), "",
                  f"Trích dẫn: **{entry['attribution']}**. Năm/phiên bản/revision: `{entry['version']}`. "
                  f"URL: {entry['url']}. Truy cập: **{entry['retrieved']}**. "
                  f"Giấy phép: **{entry['licence']}** ({licences.get(entry['licence'], '')}).", ""]
    cols = ["skills", "skill_aliases", "skill_edges", "universities", "university_aliases", "job_titles", "categories"]
    lines += ["## Số dòng theo nguồn", "", "| Nguồn | " + " | ".join(cols) + " |", "|---|" + "---:|" * len(cols)]
    counts = {table: Counter(r["source"].split(":", 1)[0] for r in rows) for table, rows in tables.items()}
    for prefix in sorted({e["prefix"] for e in manifest["files"]}):
        lines.append("| " + prefix + " | " + " | ".join(str(counts[c][prefix]) for c in cols) + " |")
    lines += ["| **Tổng** | " + " | ".join(str(len(tables[c])) for c in cols) + " |", "",
              "## Phương pháp và giới hạn", "",
               "- Gộp công nghệ khảo sát 2024–2026; ưu tiên tên của năm mới nhất, chỉ đọc response của câu hỏi công nghệ được cho phép. Không dùng nhãn lát cắt/nhóm người trả lời; loại Other và các câu hỏi AIModels, LLM, CommPlatform, SOTags, BuildTool, Disruption, TechDropDown.",
               "- Lựa chọn ghép HTML/CSS được tách thêm thành các entity Wikidata được chấp nhận trong survey_components; mỗi công nghệ có canonical/alias riêng. Tên đầy đủ và acronym trong ngoặc của lựa chọn khảo sát được giữ làm alias dẫn nguồn khảo sát.",
              "- Categories giữ taxonomy của dự án (16 nhóm), ánh xạ từ loại câu hỏi khảo sát/lớp Wikidata và ESCO; không phải taxonomy chính thức của một nhà xuất bản. Cột source của categories dẫn đến một nguồn làm cơ sở ánh xạ (khảo sát, lớp Wikidata hoặc ESCO); nhóm chưa có skill dùng nguồn khảo sát tham chiếu. Không khẳng định nhãn nhóm do Stack Overflow xuất bản.",
               "- Gap-fill: chỉ đếm nhãn skills/tech_stack trong data/clean/silver_dataset.jsonl và data/synth_v3/profiles/*.jsonl (hồ sơ tổng hợp/hư cấu). Gộp tần suất theo key chuẩn hóa trên các nguồn được phép, chỉ tra key xuất hiện ≥ 2 lần và không trùng tên khảo sát; thử tối đa 5 biến thể bề mặt phổ biến nhất. Không đọc data/real_test/ hoặc dataset/. Không lưu từ vựng đầu vào, CV hoặc dữ liệu cá nhân vào sources; chỉ lưu entity công khai được chấp nhận.",
                "- Tìm wbsearchentities tiếng Anh, tối đa 5 ứng viên mỗi truy vấn; thử bỏ hậu tố JS/.js, tách dấu / và phần trong ngoặc. Danh sách thuật ngữ công khai trong yêu cầu nghiệm thu cũng được dùng làm truy vấn, không làm tri thức. Chỉ nhận tên khớp chính xác label/alias công khai và có bằng chứng SPARQL P31/P279* hoặc P279* thuộc lớp được phép; không dùng LLM để bù dữ liệu.",
                "- Đọc nhãn en/vi và nhãn trung lập ngôn ngữ mul, bật languagefallback (nhiều tên sản phẩm đã chuyển sang mul). Tra thêm tên/alias chính xác và title enwiki trên Wikidata cho danh sách thuật ngữ công khai khi top 5 bị lấn bởi người/địa danh. Chỉ chuẩn hóa dấu câu khi so tên. Alias ghép tên với @scope/package được tách hai phần từ chính chuỗi công khai; không thêm tên thủ công.",
                "- Lớp công nghệ được phép (TECH_CLASSES): " + "; ".join(f"{qid} → {category}" for qid, category in TECH_CLASSES.items()) + ".",
                "- Q65938634 (quality control method) chỉ nhận khi P1269=Q950250 (test-driven development); không nhận trò chơi chỉ vì thuộc phần mềm. Kỹ năng mềm trùng nhãn chọn concept có nhiều sitelink nhất. Linker chuẩn hóa riêng Soft Skill tiếng Việt bằng bỏ từ nối theo và tiền tố danh hóa chủ nghĩa; chỉ nhận khi duy nhất một chủ sở hữu từ nguồn, không thêm dòng alias vào seed.",
              "- Stack Overflow tags: với từ vựng gap-fill, thử các cách viết tag (dấu cách → '-', bỏ '-', '/', '.'), nhận tag có ≥ 500 câu hỏi, lấy tag đồng nghĩa; chỉ thêm skill khi key chưa thuộc nguồn khác. Tên hiển thị là cách viết thuật ngữ trong từ vựng tổng hợp đã khớp tag.",
              "- Tên hiển thị: lựa chọn ghép của khảo sát (HTML/CSS) giữ đúng phần tên trong khảo sát; nhãn Wikidata viết thường được viết hoa chữ cái đầu (scrum → Scrum).",
              "- Trường: sinh biến thể chính tả của tên đã công bố (Ho Chi Minh City ↔ HCMC/TP HCM, \"Cao đẳng X\" ↔ \"X College\"), cùng nguồn với tên gốc; không thêm tên mới.",
              "- Quan hệ: P277 → REQUIRES chỉ với framework/library; P361 → PART_OF; P527 → PART_OF đảo chiều. Chỉ giữ hai đầu có trong KB. Đây là quan hệ tri thức từ nguồn, không phải khẳng định ứng viên thành thạo công nghệ phụ thuộc.",
              f"- Loại {summary['alias_collisions']} key alias skill mơ hồ (bỏ mọi chủ sở hữu); {summary['school_alias_collisions']} key trường mơ hồ; {summary['job_alias_collisions']} key nghề mơ hồ. Alias thông dụng như cake bị chặn. Loại {summary['cycle_edges_dropped']} cạnh tự lặp/tạo chu trình theo thứ tự ổn định trên đồ thị hợp nhất.",
                "- Trường đại học/cao đẳng: P17=Q881, P31/P279* thuộc university Q3918, academy Q38723, college Q189004, community college Q1336920, vocational school Q322563/Q2696153 hoặc academic institution Q4671277. Nhãn lớp được kiểm chứng bằng SPARQL trong wikidata_classes.json. Ghép duy nhất bằng tên đầy đủ vi/en hoặc phần trước dấu phẩy (bỏ đơn vị mẹ), không ghép riêng acronym. Bổ sung trường chưa khớp từ query; canonical vi rồi en; alias en/vi, P1813 và title enwiki/viwiki công khai trên Wikidata. university_alias_blocklist.csv là luật an toàn, không phải nguồn tri thức.",
                "- ESCO không có nhãn tiếng Việt; Wikidata bổ sung nhãn/alias kỹ năng mềm en/vi. esco_matches ghép duy nhất QID với skill thành viên ESCO bằng label/alias công khai, chuẩn hóa hình thái danh từ/động từ (-ing/-ment/-s) và thứ tự token; không ghép nhóm skills-hierarchy. Hai nguồn dùng cùng canonical, không sinh skill trùng; concept chưa ghép là Soft Skill độc lập. Tên nghề gồm nhãn ưu tiên và nhãn thay thế tiếng Anh; một dòng cho mỗi alias duy nhất.",
              "- Snapshot là các thời điểm độc lập; Wikidata có thể thay đổi/lỗi thời. Dựng offline tái lập từ manifest không cần truy cập dữ liệu tổng hợp. Fetch dùng cache SHA-256; --refresh để tải lại. Năm khảo sát không có sẽ được ghi unavailable trong manifest.", ""]
    (output / "SOURCES.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=ROOT / "sources")
    parser.add_argument("--out", type=Path, default=ROOT / "seed")
    args = parser.parse_args(argv)
    print(json.dumps(build_external(args.sources, args.out), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
