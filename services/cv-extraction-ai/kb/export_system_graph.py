"""Write the shared skill graph used by matching and interview selection."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from app.kb.extension import graph_key, skills_mentioned
from app.kb.store import KnowledgeBase
from app.postprocess.text_match import normalize

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
SEED = ROOT / "kb" / "seed"
OUTPUTS = (
    ROOT.parent / "cv-matching-ai" / "data" / "kb_skill_graph.json",
    REPO / "backend" / "common" / "src" / "main" / "resources" / "kb" / "skill_graph.json",
)


def build_payload(seed_dir: Path = SEED) -> dict:
    kb = KnowledgeBase.from_csv(seed_dir)
    id_to_key = {sid: graph_key(name) for sid, (name, _category) in kb.skills.items()}
    nodes = [
        {"id": id_to_key[sid], "name": name, "category": category}
        for sid, (name, category) in sorted(kb.skills.items())
        if id_to_key[sid]
    ]
    aliases: list[dict[str, str]] = []
    seen_alias: set[str] = set()
    for surface, sid in kb.linker.surfaces.items():
        source = graph_key(surface)
        target = id_to_key.get(sid, "")
        if source and target and source != target and source not in seen_alias:
            seen_alias.add(source)
            aliases.append({"from": source, "to": target})
    edges = []
    seen: set[tuple[str, str, str]] = set()
    for src, relations in kb.edges.items():
        for rel, dst in relations:
            pair = (id_to_key.get(src, ""), rel, id_to_key.get(dst, ""))
            if not pair[0] or not pair[2] or pair[0] == pair[2] or pair in seen:
                continue
            seen.add(pair)
            edges.append({"from": pair[0], "to": pair[2], "rel": rel})
    job_skills: dict[str, list[str]] = {}
    titles = seed_dir / "job_titles.csv"
    if titles.exists():
        with titles.open(encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                title = row["name"].strip()
                mentioned = skills_mentioned(title, kb.skills)
                if mentioned:
                    job_skills[normalize(title)] = mentioned
    return {"nodes": nodes, "aliases": aliases, "edges": edges, "job_skills": job_skills}


def main() -> None:
    payload = build_payload()
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    for path in OUTPUTS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"{path} nodes={len(payload['nodes'])} edges={len(payload['edges'])}")


if __name__ == "__main__":
    main()
