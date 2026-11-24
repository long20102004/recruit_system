"""Build KB1 facts from official PDFs using Poppler; never persist book prose.

Run from ai-service: .venv/bin/python -m kb.books
Pages in the snapshot are printed book pages (1-based). PDF offsets are inferred
from chapter headings. Page-granular section ranges include the shared boundary
page; counts are surface occurrences, not claims of semantic understanding.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
from itertools import combinations
from pathlib import Path
import re
import subprocess

from app.kb.candidates import CandidateSkillFinder
from app.kb.store import KnowledgeBase
from app.postprocess.text_match import normalize, normalize_with_map
from kb.fetch_sources import Fetcher, ROOT, USER_AGENT

BOOKS = (
    dict(id="progit", title="Pro Git", authors=["Scott Chacon", "Ben Straub"],
         edition="2", licence="CC BY-NC-SA 3.0",
         url="https://github.com/progit/progit2/releases/download/2.1.450/progit.pdf"),
    dict(id="thinkpython", title="Think Python", authors=["Allen B. Downey"],
         edition="2", licence="CC BY-NC 3.0",
         url="https://greenteapress.com/thinkpython2/thinkpython2.pdf"),
)


def pdf_text(path: Path, first: int, last: int) -> str:
    return subprocess.run(
        ["pdftotext", "-layout", "-f", str(first), "-l", str(last), str(path), "-"],
        check=True, capture_output=True, text=True, timeout=60,
    ).stdout


def pdf_pages(path: Path) -> int:
    info = subprocess.run(["pdfinfo", str(path)], check=True, capture_output=True,
                          text=True, timeout=30).stdout
    return int(re.search(r"^Pages:\s+(\d+)", info, re.M).group(1))


def download_pdf(fetcher: Fetcher, book: dict, cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{book['id']}.pdf"
    if path.exists() and not fetcher.refresh:
        pdf_pages(path)  # Fail explicitly on a truncated cache rather than use it.
        return path
    temporary = path.with_suffix(".pdf.part")
    # curl -4 avoids broken IPv6 routes on some builders; bounded total runtime
    # also covers DNS/redirect stalls not bounded by requests' read timeout.
    subprocess.run([
        "curl", "-4", "--fail", "--silent", "--show-error", "--location",
        "--retry", "2", "--connect-timeout", "20", "--max-time", "600",
        "--user-agent", USER_AGENT, "--output", str(temporary), book["url"],
    ], check=True, timeout=1900)
    pdf_pages(temporary)
    temporary.replace(path)
    return path


def parse_toc(text: str, book_id: str) -> list[dict]:
    """Parse numbered chapter/section rows, accepting dotted/spaced leaders.

    Only pages headed Contents/Table of Contents are read, avoiding body text.
    Appendix A / A and A.1 forms are accepted alongside numeric chapters.
    """
    sections, seen, parent = [], set(), None
    toc_pages, active = [], False
    for page_text in text.split("\f"):
        headed = re.search(r"(?im)^\s*(?:[ivxlcdm]+\s+)?(?:Table of )?Contents(?:\s+[ivxlcdm]+)?\s*$", page_text)
        dotted = len(re.findall(r"(?m)\.(?:\s*\.)+\s*\d+\s*$", page_text))
        if not headed and not (active and dotted):
            active = False
            continue
        active = True
        toc_pages.append(page_text)
    # Asciidoctor's Pro Git PDF has unnumbered headings and indentation instead
    # of numeric section labels, including continuation pages without a header.
    if book_id == "progit" and not re.search(r"(?m)^\s*1(?:\.|\s)\s*\w", "\n".join(toc_pages)):
        rows = []
        for line in "\n".join(toc_pages).splitlines():
            match = re.match(r"^(\s*)(.+?)\s*\.(?:\s*\.)+\s*(\d+)\s*$", line)
            if match:
                rows.append((len(match[1]), match[2].strip(), int(match[3])))
        chapter, child = 0, 0
        for index, (indent, title, page) in enumerate(rows):
            if indent == 0:
                # Exclude front matter and index: actual chapters have children.
                parent = None
                if index + 1 == len(rows) or rows[index + 1][0] == 0:
                    continue
                appendix = re.match(r"Appendix ([A-Z]):\s*(.+)", title)
                if appendix:
                    number, title = appendix.groups()
                else:
                    chapter += 1
                    number = str(chapter)
                parent, child = f"{book_id}:{number}", 0
                sections.append(dict(id=parent, title=title, level=1, page=page,
                                     parent=None, mentions={}))
            elif parent:
                child += 1
                sections.append(dict(id=f"{parent}.{child}", title=title, level=2,
                                     page=page, parent=parent, mentions={}))
        if not sections:
            raise ValueError(f"No table of contents found for {book_id}")
        return sections
    for page_text in toc_pages:
        for line in page_text.splitlines():
            match = re.match(
                r"^\s*(?:Chapter\s+|Appendix\s+)?(?P<num>\d+(?:\.\d+)?|[A-Z](?:\.\d+)?)"
                r"\.?\s+(?P<title>.+?)(?:\s*\.(?:\s*\.)+\s*|\s{2,})(?P<page>\d+)\s*$",
                line,
            )
            if not match:
                continue
            number = match["num"]
            sid = f"{book_id}:{number}"
            level = 2 if "." in number else 1
            if sid in seen:
                continue
            if level == 1:
                parent = sid
            elif parent != f"{book_id}:{number.split('.')[0]}":
                raise ValueError(f"Orphan TOC section: {sid}")
            title = re.sub(r"\s+", " ", match["title"]).strip(" .")
            sections.append(dict(id=sid, title=title, level=level, page=int(match["page"]),
                                 parent=parent if level == 2 else None, mentions={}))
            seen.add(sid)
    if not sections:
        raise ValueError(f"No table of contents found for {book_id}")
    return sections


def detect_offset(sections: list[dict], pages: list[str]) -> int:
    """Vote on PDF-page minus printed-page using chapter headings, not TOC rows."""
    votes = Counter()
    for section in sections:
        if section["level"] != 1:
            continue
        title = normalize(section["title"])
        candidates = []
        for index, text in enumerate(pages, 1):
            lines = [normalize(line) for line in text.splitlines() if line.strip()]
            # Chapter titles are isolated near the top; TOC rows carry page numbers.
            if title in lines[:10]:
                candidates.append(index - section["page"])
        votes.update(set(candidates))
    if not votes or votes.most_common(1)[0][1] < 2:
        raise ValueError("Cannot establish printed/PDF page offset from chapter headings")
    return votes.most_common(1)[0][0]


_SINGLE_WORD = re.compile(r"[A-Za-z]+")


def build_finder(kb: KnowledgeBase) -> CandidateSkillFinder:
    """Matcher for prose: book text is full of everyday words that are also skill aliases
    ("word" -> Microsoft Word, "lists" -> Microsoft Lists, "access" -> Microsoft Access).

    * single plain words are matched only as the skill's own canonical name, case-sensitively
      ("Python", "Git"), never as an alias;
    * every other surface (several words, or with digits / ".", "#", "+") is matched
      case-insensitively as before.
    """
    allowed = {sid: name for sid, (name, category) in kb.skills.items() if category != "Soft Skill"}
    surfaces: dict[str, str] = {}
    words: dict[str, str] = {}
    for name in allowed.values():
        (words if _SINGLE_WORD.fullmatch(name) else surfaces).__setitem__(name, name)
    for surface, sid in kb.linker.surfaces.items():
        surface = surface.strip()
        if len(surface) > 3 and sid in allowed and not _SINGLE_WORD.fullmatch(surface):
            surfaces.setdefault(surface, allowed[sid])
    finder = CandidateSkillFinder(surfaces)
    finder._case_words = [(re.compile(rf"(?<![\w#+.]){re.escape(w)}(?![\w#+])"), name)  # type: ignore[attr-defined]
                          for w, name in sorted(words.items())]
    return finder


def count_mentions(text: str, finder: CandidateSkillFinder) -> dict[str, int]:
    """Distinct (canonical, start) occurrences; single words case-sensitive (see build_finder)."""
    positions = defaultdict(set)
    normalized, char_map = normalize_with_map(text)
    for pattern, name in getattr(finder, "_case_words", []):
        for match in pattern.finditer(text):
            positions[name].add(match.start())
    for pattern, name in finder._short_patterns:
        for match in pattern.finditer(text):
            positions[name].add(match.start())
    for pattern, name in finder._special_long_patterns:
        positions[name].update(char_map[match.start()] for match in pattern.finditer(normalized))
    for pattern in finder._batched_long_patterns:
        for match in pattern.finditer(normalized):
            positions[finder._norm_to_canonical[match.group(1)]].add(char_map[match.start()])
    return {name: len(found) for name, found in sorted(positions.items()) if found}


def related_skills(book_id: str, sections: list[dict]) -> list[dict]:
    # Use leaf sections, not their aggregate chapter containers: a chapter and
    # its child are not two independent pieces of co-occurrence evidence.
    parents = {s["parent"] for s in sections if s["parent"]}
    counts = Counter(pair for section in sections if section["id"] not in parents
                     for pair in combinations(sorted(section["mentions"]), 2))
    return [dict(a=a, b=b, sections=count, source=book_id)
            for (a, b), count in sorted(counts.items()) if count >= 2]


def build_book(book: dict, path: Path, finder: CandidateSkillFinder) -> dict:
    total = pdf_pages(path)
    # Poppler pdftotext has no outline export; parse the printed front-matter TOC.
    sections = parse_toc(pdf_text(path, 1, min(40, total)), book["id"])
    pages = pdf_text(path, 1, total).split("\f")[:total]
    offset = detect_offset(sections, pages)
    # Index entries are not section text (and would inflate technology counts).
    content_end = next((i - 1 for i, text in enumerate(pages, 1)
                        if i > sections[-1]["page"] + offset
                        and re.match(r"^\s*Index\s*\n", text)), total)
    for index, section in enumerate(sections):
        following = next((s for s in sections[index + 1:] if s["level"] <= section["level"]), None)
        first = section["page"] + offset
        last = min(content_end, following["page"] + offset if following else content_end)
        if not 1 <= first <= last <= total:
            raise ValueError(f"Invalid page range for {section['id']}: {first}-{last}")
        section["mentions"] = count_mentions(pdf_text(path, first, last), finder)
    return dict(book, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), sections=sections)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args(argv)
    fetcher = Fetcher(ROOT / "sources", refresh=args.refresh)
    finder = build_finder(KnowledgeBase.from_csv(ROOT / "seed"))
    books = [build_book(book, download_pdf(fetcher, book, ROOT / ".cache/books"), finder)
             for book in BOOKS]
    related = [relation for book in books for relation in related_skills(book["id"], book["sections"])]
    fetcher.save(
        "kb1_books.json", dict(books=books, related=related),
        url=" ; ".join(book["url"] for book in BOOKS),
        version="Pro Git 2.1.450; Think Python 2e",
        licence="CC BY-NC-SA 3.0 (Pro Git); CC BY-NC 3.0 (Think Python)",
        attribution="Scott Chacon and Ben Straub (Pro Git); Allen B. Downey (Think Python)",
        prefix="book", pdf_sha256={book["id"]: book["sha256"] for book in books},
    )
    for book in books:
        sections = book["sections"]
        print(f"{book['id']}: {sum(s['level'] == 1 for s in sections)} chapters/appendices, "
              f"{sum(s['level'] == 2 for s in sections)} sections, "
              f"{len(set().union(*(s['mentions'] for s in sections)))} skills, "
              f"{sum(r['source'] == book['id'] for r in related)} related")


if __name__ == "__main__":
    main()
