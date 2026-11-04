"""Render fictional JSONL profiles to HTML/PDF and ground labels in PDFBox text.

Run from ai-service: python -m training.synth.render --profiles data/synth_v3/profiles
--out data/synth_v3. No model or optional template/HTTP library is required.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.request import Request, urlopen
import uuid

from app.postprocess.schema import ITEM_KEYS, PERSONAL_INFO_KEYS
from app.postprocess.text_match import contains, normalize


LAYOUTS = tuple(f"L{i}" for i in range(1, 11))
PROGRAMMING_LANGUAGES = {
    "java", "javascript", "typescript", "python", "go", "golang", "c", "c++",
    "c#", "csharp", "c sharp", "php", "ruby", "rust", "kotlin", "swift",
    "scala", "dart", "r", "sql", "bash", "perl", "objective-c", "matlab",
    "html", "css", "lua", "elixir", "haskell", "visual basic", "vb.net",
}
PROFILE_KEYS = {
    "personal_info", "objective", "education", "experience", "personal_projects",
    "skills", "certificates", "honours", "languages",
}


def validate_profile(record: object) -> list[str]:
    """Return privacy-safe reason codes; never coerce or rewrite label values."""
    reasons: set[str] = set()

    def walk(value: object) -> None:
        if isinstance(value, str) and ("\n" in value or "\r" in value):
            reasons.add("multiline_string")
        elif isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    def scalar(value: object, integer: bool = False) -> bool:
        if value is None:
            return True
        return type(value) is int if integer else isinstance(value, str) and bool(value.strip())

    def string_list(value: object) -> bool:
        return isinstance(value, list) and all(
            isinstance(item, str) and bool(item.strip()) for item in value
        )

    walk(record)
    if not isinstance(record, dict):
        return ["schema"]
    if not {"id", "level", "lang", "role", "profile", "extras"} <= record.keys():
        reasons.add("schema")
    if not isinstance(record.get("id"), str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", record.get("id", "")
    ):
        reasons.add("invalid_id")
    if record.get("level") not in ("junior", "middle", "senior", "lead"):
        reasons.add("invalid_level")
    if record.get("lang") not in ("en", "vi"):
        reasons.add("invalid_lang")
    if not isinstance(record.get("role"), str):
        reasons.add("schema")
    p = record.get("profile")
    if not isinstance(p, dict) or set(p) != PROFILE_KEYS:
        reasons.add("schema")
        return sorted(reasons)
    info = p.get("personal_info")
    if not isinstance(info, dict) or set(info) != set(PERSONAL_INFO_KEYS):
        reasons.add("schema")
    elif not all(scalar(value) for value in info.values()):
        reasons.add("schema")
    if not scalar(p.get("objective")):
        reasons.add("schema")
    for section in ("skills", "certificates", "honours"):
        if not string_list(p.get(section)):
            reasons.add("schema")
    for section, keys in ITEM_KEYS.items():
        items = p.get(section)
        if not isinstance(items, list):
            reasons.add("schema")
            continue
        for item in items:
            if not isinstance(item, dict) or set(item) != set(keys):
                reasons.add("schema")
                continue
            for key, value in item.items():
                valid = string_list(value) if key in ("description", "tech_stack") else scalar(
                    value, key in ("start_year", "end_year", "team_size")
                )
                if not valid:
                    reasons.add("schema")
            if section == "languages" and isinstance(item.get("language"), str):
                language = normalize(item["language"])
                # Also reject common proficiency suffixes, e.g. "Python (Advanced)".
                if any(re.match(re.escape(name) + r"(?:$|[\s(/:])", language)
                       for name in PROGRAMMING_LANGUAGES):
                    reasons.add("programming_language")
    extras = record.get("extras")
    if not isinstance(extras, dict):
        reasons.add("schema")
    else:
        if not {"headline", "address", "dob", "linkedin", "skill_groups", "interests"} <= extras.keys():
            reasons.add("schema")
        if not all(scalar(extras.get(k)) for k in ("headline", "address", "dob", "linkedin")):
            reasons.add("schema")
        if not string_list(extras.get("interests")):
            reasons.add("schema")
        groups = extras.get("skill_groups")
        if not isinstance(groups, list) or any(
            not isinstance(g, dict) or set(g) != {"group", "items"}
            or not isinstance(g.get("group"), str) or not string_list(g.get("items"))
            for g in (groups if isinstance(groups, list) else [])
        ):
            reasons.add("schema")
        elif [v for g in groups for v in g["items"]] != p.get("skills"):
            reasons.add("skill_groups_mismatch")
    return sorted(reasons)


def _e(value: object) -> str:
    return "" if value is None else html.escape(str(value), quote=True)


def render_html(record: dict, layout: str) -> str:
    """Build one of ten layouts, escaping all supplied content verbatim."""
    if layout not in LAYOUTS:
        raise ValueError("Unknown layout")
    p, x = record["profile"], record["extras"]
    vi = record["lang"] == "vi"
    present = "Hiện tại" if vi else "Present"
    titles = dict(zip(
        ("summary", "experience", "education", "skills", "certificates", "honours", "languages", "projects"),
        ("Mục tiêu nghề nghiệp", "KINH NGHIỆM LÀM VIỆC", "HỌC VẤN", "KỸ NĂNG", "CHỨNG CHỈ", "GIẢI THƯỞNG", "NGOẠI NGỮ", "DỰ ÁN")
        if layout == "L3" and vi else
        ("Objective" if layout == "L8" else "Summary", "Work Experience", "Education", "Skills", "Certifications", "Awards", "Languages", "Projects"),
    ))

    def section(key: str, body: str, title: str | None = None) -> str:
        if not body:
            return ""
        heading = title or titles[key]
        if layout == "L1":
            heading = "EXPERIENCE" if key == "experience" else heading.upper()
        return f'<section><h2>{_e(heading)}</h2>{body}</section>'

    def paragraph(value: object) -> str:
        return f"<p>{_e(value)}</p>" if value is not None else ""

    def bullets(items: list) -> str:
        marker = "-" if layout == "L9" else "•"
        return "".join(f'<p class="bullet">{marker} {_e(v)}</p>' for v in items)

    def dates(item: dict, years: bool = False) -> str:
        start, end = ("start_year", "end_year") if years else ("start_date", "end_date")
        return f'{_e(item[start])} - {_e(item[end]) if item[end] is not None else present}'

    info = p["personal_info"]
    header = f'<header><h1>{_e(info["full_name"])}</h1>{paragraph(x["headline"])}'
    contact = "".join(paragraph(info[k]) for k in ("email", "phone", "github_url"))
    if layout != "L2":
        header += contact
    header += "".join(paragraph(x[k]) for k in ("address", "dob", "linkedin")) + "</header>"
    summary = section("summary", paragraph(p["objective"]))
    city = (x["address"] or "").rsplit(",", 1)[-1].strip()
    jobs = []
    for job in p["experience"]:
        company, title = _e(job["company"]), _e(job["job_title"])
        date, desc = dates(job), bullets(job["description"])
        if layout == "L4":
            body = f'<p>{company} — {_e(city)} | {title} | {date}</p>{desc}'
        elif layout == "L5":
            body = f'<table><tr><td><p>{title}</p><p>{company}, {_e(city)}</p></td><td class="date">{date}</td></tr></table>{desc}'
        elif layout == "L10":
            body = f'<table><tr><td class="timeline">{date}</td><td><p>{company}</p><p>{title}</p>{desc}</td></tr></table>'
        else:
            body = f"<p>{company} | {title}</p><p>{date}</p>{desc}"
        jobs.append(f'<div class="entry">{body}</div>')
    experience = section("experience", "".join(jobs))
    education = section("education", "".join(
        '<div class="entry">' + paragraph(item["school"]) + paragraph(item["major"])
        + paragraph(dates(item, True)) + paragraph(item["gpa"]) + "</div>"
        for item in p["education"]
    ))
    groups = x["skill_groups"]
    if layout == "L8":
        skill_body = paragraph("Skills: " + ", ".join(p["skills"])) if p["skills"] else ""
    elif layout == "L6":
        skill_body = "<table>" + "".join(
            f'<tr><td>{_e(g["group"])}</td><td>{_e(", ".join(g["items"]))}</td></tr>'
            for g in groups
        ) + "</table>" if groups else ""
    else:
        skill_body = "".join(paragraph(g["group"] + ": " + ", ".join(g["items"])) for g in groups)
    skills = section("skills", skill_body)
    language_values = [item["language"] + (f' ({item["note"]})' if item["note"] else "")
                       for item in p["languages"] if item["language"] is not None]
    languages = section("languages", paragraph("Languages: " + ", ".join(language_values))
                        if layout == "L8" and language_values else "".join(map(paragraph, language_values)))
    certificates = section("certificates", bullets(p["certificates"]))
    honours = section("honours", bullets(p["honours"]))
    if layout == "L9":
        certificates = section("certificates", "<p>Certifications:</p>" + bullets(p["certificates"])
                               + "<p>Awards:</p>" + bullets(p["honours"]), "Certifications & Awards")
        honours = ""
    projects = []
    for item in p["personal_projects"]:
        body = paragraph(item["name"])
        if item["role"] is not None:
            body += paragraph("Role: " + item["role"])
        if item["team_size"] is not None:
            body += paragraph(f'Team size: {item["team_size"]}')
        body += paragraph(dates(item)) + paragraph(item["github_url"]) + bullets(item["description"])
        tech = item["tech_stack"]
        if tech:
            if layout == "L7":
                split = (len(tech) + 1) // 2
                text = "Backend(" + ", ".join(tech[:split]) + ")"
                if tech[split:]:
                    text += ", Frontend(" + ", ".join(tech[split:]) + ")"
                body += paragraph("Tech: " + text)
            else:
                body += paragraph("Tech: " + ", ".join(tech))
        projects.append(f'<div class="entry">{body}</div>')
    projects_html = section("projects", "".join(projects))
    if layout == "L2":
        # Explicit HTML widths/valign are respected by LibreOffice's HTML importer
        # more consistently than CSS alone (especially on table cells).
        body = header + f'<table class="columns"><tr><td class="sidebar" width="32%" valign="top">{contact}{skills}{languages}{certificates}</td><td width="68%" valign="top">{summary}{experience}{projects_html}{education}{honours}</td></tr></table>'
    else:
        body = header + summary + experience + education + skills + projects_html + certificates + honours + languages
    # No text-transform, hyphenation or manual wrapping: labels must survive PDFBox.
    css = """
        @page { size: A4; margin: 14mm; }
        body { font-family: "Liberation Sans", sans-serif; font-size: 10pt; line-height: 1.25; }
        h1 { font-size: 21pt; margin: 0 0 5pt; }
        h2 { font-size: 12pt; margin: 12pt 0 5pt; page-break-after: avoid; }
        p { margin: 3pt 0; hyphens: none; }
        table { width: 100%; border-collapse: collapse; }
        td { vertical-align: top; padding: 3pt 6pt; }
        .sidebar { width: 32%; background: #eef2f5; }
        .sidebar p { font-size: 8pt; }
        .sidebar h2 { font-size: 10pt; }
        .columns > tbody > tr > td { padding: 8pt; }
        .date { width: 28%; text-align: right; }
        .timeline { width: 24%; border-right: 1pt solid #718096; }
        .entry { margin-bottom: 8pt; }
        .bullet { margin-left: 7pt; }
    """
    if layout == "L9":
        css += "h2 { border-bottom: 1pt solid #555; padding-bottom: 3pt; }"
    return f'<!DOCTYPE html><html lang="{record["lang"]}"><head><meta charset="utf-8"><title>CV</title><style>{css}</style></head><body>{body}</body></html>'


def ground_label(profile: dict, text: str) -> tuple[dict, Counter]:
    """Keep original values only when grounded; count every removed leaf by path.

    Integers retain their schema types (normalize_profile coerces years to strings,
    so it must not be used here). Missing anchors discard their whole item.
    """
    label = deepcopy(profile)
    cv_norm = normalize(text)
    dropped: Counter = Counter()

    def ground(value: object, path: str, force: bool = False) -> object:
        if isinstance(value, dict):
            return {key: ground(child, f"{path}.{key}", force) for key, child in value.items()}
        if isinstance(value, list):
            return [kept for child in value if (kept := ground(child, path, force)) is not None]
        if value is not None and (force or not contains(cv_norm, str(value))):
            dropped[path] += 1
            return None
        return value

    for section, anchor in (("education", "school"), ("experience", "company"),
                            ("personal_projects", "name"), ("languages", "language")):
        kept = []
        for item in label[section]:
            missing = not item[anchor] or not contains(cv_norm, item[anchor])
            grounded = ground(item, section, missing)
            if not missing:
                kept.append(grounded)
        label[section] = kept
    for key in ("personal_info", "objective", "skills", "certificates", "honours"):
        label[key] = ground(label[key], key)
    return label, dropped


def load_profiles(directory: Path) -> tuple[list[dict], Counter]:
    """Read in deterministic ID order; duplicate IDs are skipped, not overwritten."""
    invalid: Counter = Counter()
    records = []
    seen: set[str] = set()
    for path in sorted(directory.rglob("*.jsonl")):
        with path.open(encoding="utf-8") as source:
            for line in source:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    invalid["invalid_json"] += 1
                    continue
                reasons = validate_profile(record)
                if reasons:
                    invalid.update(reasons)
                    continue
                if record["id"] in seen:
                    invalid["duplicate_id"] += 1
                    continue
                seen.add(record["id"])
                records.append(record)
    return sorted(records, key=lambda r: r["id"]), invalid


def extract_text(pdf: Path, backend: str) -> str:
    boundary = "----cv-render-" + uuid.uuid4().hex
    payload = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
               f'filename="{pdf.name}"\r\nContent-Type: application/pdf\r\n\r\n').encode()
    payload += pdf.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    request = Request(backend.rstrip("/") + "/api/v1/cv/extract-text", data=payload,
                      headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urlopen(request, timeout=120) as response:
        result = json.load(response)
    if not isinstance(result, dict) or not isinstance(result.get("text"), str) or not result["text"].strip():
        raise ValueError("Backend returned no extracted text")
    return result["text"]


def run(profiles: Path, out: Path, backend: str, limit: int | None = None, layout_offset: int = 0) -> dict:
    if not profiles.is_dir():
        raise ValueError("Profiles directory does not exist")
    if limit is not None and limit < 0:
        raise ValueError("Limit must be nonnegative")
    if not shutil.which("soffice"):
        raise RuntimeError("soffice is required")
    records, invalid = load_profiles(profiles)
    selected = [(r, LAYOUTS[(i + layout_offset) % len(LAYOUTS)]) for i, r in enumerate(records)][:limit]
    for directory in (out / "html", out / "pdf", out / "tmp"):
        directory.mkdir(parents=True, exist_ok=True)
    summary = {"rendered": 0, "by_layout": Counter(), "by_level": Counter(),
               "by_lang": Counter(), "invalid_profiles_by_reason": invalid,
               "dropped_values_by_field": Counter(),
               "dropped_values_by_layout": {layout: Counter() for layout in LAYOUTS}}
    for record, layout in selected:
        (out / "html" / f'{record["id"]}.html').write_text(render_html(record, layout), encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="render-", dir=out / "tmp") as tmp:
        work = Path(tmp).resolve()
        # Separate LO profile avoids forwarding to a GUI instance or another run.
        for start in range(0, len(selected), 50):
            batch = selected[start:start + 50]
            command = ["soffice", f"-env:UserInstallation={(work / 'lo').as_uri()}",
                       "--headless", "--convert-to", "pdf", "--outdir", str(work)]
            command += [str((out / "html" / f'{r["id"]}.html').resolve()) for r, _ in batch]
            try:
                subprocess.run(command, check=True, capture_output=True, timeout=300)
            except (subprocess.SubprocessError, OSError):
                raise RuntimeError("LibreOffice conversion failed") from None
            for record, _ in batch:
                pdf = work / f'{record["id"]}.pdf'
                if not pdf.is_file():
                    raise RuntimeError("LibreOffice did not produce every PDF")
                shutil.move(str(pdf), out / "pdf" / pdf.name)
        # Publish JSONL atomically, so failures do not leave a partial dataset.
        rendered = work / "rendered.jsonl"
        with rendered.open("w", encoding="utf-8") as target:
            for record, layout in selected:
                try:
                    text = extract_text(out / "pdf" / f'{record["id"]}.pdf', backend)
                except Exception:
                    raise RuntimeError("PDFBox extraction failed; check backend availability/response") from None
                label, dropped = ground_label(record["profile"], text)
                row = {key: record[key] for key in ("id", "level", "lang")}
                row.update(layout=layout, input=text, output=json.dumps(label, ensure_ascii=False))
                target.write(json.dumps(row, ensure_ascii=False) + "\n")
                summary["rendered"] += 1
                for key in ("layout", "level", "lang"):
                    summary[f"by_{key}"][layout if key == "layout" else record[key]] += 1
                summary["dropped_values_by_field"].update(dropped)
                summary["dropped_values_by_layout"][layout].update(dropped)
        rendered.replace(out / "rendered.jsonl")
    (out / "render_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--backend", default="http://localhost:8080")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--layout-offset", type=int, default=0, help="shift the layout rotation (second rendering pass)")
    args = parser.parse_args()
    try:
        summary = run(args.profiles, args.out, args.backend, args.limit, args.layout_offset)
    except (ValueError, RuntimeError) as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
