"""Reading-order check of two PDF text extractions against gold labels (feature 011).

    python -m eval.layout_check --old data/real_test/text --new data/real_test/text_col \
        --labels data/retrain_v3/test_real.jsonl data/real_test/train_real_v3.jsonl

For every labelled CV whose old text matches a file in --old, counts how many gold strings
(companies, titles, schools, project names, bullets) are contiguous in each extraction.
A CV is "two-column" when >= 15 % of its old lines no longer appear whole in the new text
(the layout extractor split lines that mixed two columns). Counts only, no CV content.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from collections import Counter

from app.postprocess.text_match import normalize


def _key(text: str) -> str:
    return " ".join(normalize(text).split())


def _load(folder: str) -> dict[str, str]:
    out = {}
    for path in glob.glob(os.path.join(folder, "*.json")):
        data = json.load(open(path, encoding="utf-8"))
        if "text" in data:
            out[os.path.basename(path)[:-5]] = data["text"]
    return out


def _gold_strings(gold: dict) -> list[tuple[str, str]]:
    out = []
    for e in gold.get("experience") or []:
        out += [("company", e.get("company")), ("title", e.get("job_title"))]
        out += [("bullet", b) for b in e.get("description") or []]
    for p in gold.get("personal_projects") or []:
        out += [("project", p.get("name"))] + [("bullet", b) for b in p.get("description") or []]
    out += [("school", e.get("school")) for e in gold.get("education") or []]
    return [(t, s) for t, s in out if isinstance(s, str) and len(s.strip()) >= 4]


def _synthetic(rendered: str, new: dict[str, str]) -> None:
    """Ground truth = the generating profile, independent of any extraction: no bias."""
    per_layout: dict[str, Counter] = {}
    for line in open(rendered, encoding="utf-8"):
        row = json.loads(line)
        if row["id"] not in new:
            continue
        gold = json.loads(row["output"])
        old_key, new_key = _key(row["input"]), _key(new[row["id"]])
        t = per_layout.setdefault(row["layout"], Counter())
        t["n"] += 1
        for _, s in _gold_strings(gold):
            k = _key(s)
            t["gold"] += 1
            t["old"] += k in old_key
            t["new"] += k in new_key
    total = Counter()
    for layout in sorted(per_layout, key=lambda x: int(x[1:])):
        t = per_layout[layout]
        total.update(t)
        print(f"{layout:4} {t['n']:3} CVs | gold {t['gold']:5} | old {t['old'] / t['gold']:.0%} | new {t['new'] / t['gold']:.0%}")
    print(f"ALL  {total['n']:3} CVs | gold {total['gold']:5} | old {total['old'] / total['gold']:.0%} | new {total['new'] / total['gold']:.0%}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--old", help="folder of old-text json (real CVs)")
    ap.add_argument("--new", required=True)
    ap.add_argument("--labels", nargs="+", default=[])
    ap.add_argument("--rendered", help="synthetic rendered.jsonl (old text + ground-truth profile), unbiased")
    args = ap.parse_args(argv)
    if args.rendered:
        _synthetic(args.rendered, _load(args.new))
        return
    old, new = _load(args.old), _load(args.new)
    by_key = {_key(v): k for k, v in old.items()}
    totals = {"one": Counter(), "two": Counter()}
    per_cv = []
    for path in args.labels:
        for line in open(path, encoding="utf-8"):
            row = json.loads(line)
            name = by_key.get(_key(row["input"]))
            if not name or name not in new:
                continue
            old_lines = [_key(x) for x in old[name].splitlines() if len(x.strip()) > 15]
            new_key = _key(new[name])
            changed = sum(1 for x in old_lines if x not in new_key) / max(1, len(old_lines))
            kind = "two" if changed >= 0.15 else "one"
            gold = json.loads(row["output"])
            a = b = c = 0
            for _, s in _gold_strings(gold):
                k = _key(s)
                a += 1
                b += k in _key(old[name])
                c += k in new_key
            totals[kind].update(n=1, gold=a, old=b, new=c)
            per_cv.append((name, kind, a, b, c))
    for kind, t in totals.items():
        if t["n"]:
            print(f"{kind}-column CVs: {t['n']:2} | gold strings {t['gold']:4} | contiguous old {t['old']:4} "
                  f"({t['old'] / t['gold']:.0%}) | new {t['new']:4} ({t['new'] / t['gold']:.0%})")
    worse = [(n, k, a, b, c) for n, k, a, b, c in per_cv if c < b]
    better = [(n, k, a, b, c) for n, k, a, b, c in per_cv if c > b]
    print("worse (name, kind, gold, old, new):", worse)
    print("better:", better)


if __name__ == "__main__":
    main()
