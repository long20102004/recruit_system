"""Derive v5 profile variants from the fictional synth_v3 profiles (feature 014).

Run from ai-service/:  python -m training.synth.variants --profiles data/synth_v3/profiles --out data/synth_v5/profiles

Two shapes the v4 model never saw in training:
  many_jobs  4-6 consecutive jobs with 1-2 bullets each, plus 5-9 projects with short descriptions
             (jobs and projects borrowed from other fictional profiles of the same language,
             dates rewritten into a non-overlapping, newest-first timeline)
  student    no work experience at all, 2-5 projects (a junior profile with its jobs removed)
All inputs are fictional (profile_prompt.md); output ids are "<base id>.m" / "<base id>.s" so the
dataset builder can keep every variant of a profile on the same side of the train/dev split.
"""

from __future__ import annotations

import argparse
import json
import random
from copy import deepcopy
from pathlib import Path

from training.synth.render import load_profiles, validate_profile

SEED = 14


def _month(y: int, m: int) -> str:
    return f"{m:02d}/{y}"


def _timeline(n: int, rng: random.Random, current: bool) -> list[tuple[str, str | None]]:
    """n (start, end) pairs, newest first, non-overlapping, ending around 2025."""
    y, m = 2025, rng.randint(1, 12)
    out = []
    for i in range(n):
        end = None if (i == 0 and current) else _month(y, m)
        months = rng.randint(6, 26)
        total = y * 12 + (m - 1) - months
        sy, sm = divmod(total, 12)
        out.append((_month(sy, sm + 1), end))
        gap = rng.randint(0, 2)
        total -= gap
        y, m = divmod(total, 12)
        m += 1
    return out


def many_jobs(base: dict, pool: list[dict], rng: random.Random) -> dict:
    rec = deepcopy(base)
    p = rec["profile"]
    n = rng.randint(4, 6)
    jobs = [deepcopy(j) for j in p["experience"]]
    used = {j["company"] for j in jobs}
    donors = [d for d in pool if d["id"] != base["id"]]
    rng.shuffle(donors)
    for d in donors:
        for j in d["profile"]["experience"]:
            if len(jobs) >= n:
                break
            if j["company"] not in used:
                jobs.append(deepcopy(j))
                used.add(j["company"])
        if len(jobs) >= n:
            break
    jobs = jobs[:n]
    for job, (start, end) in zip(jobs, _timeline(len(jobs), rng, current=rng.random() < 0.6)):
        job["start_date"], job["end_date"] = start, end
        job["description"] = job["description"][: rng.randint(1, 2)]
    p["experience"] = jobs
    k = rng.randint(5, 9)
    projects = [deepcopy(x) for x in p["personal_projects"]]
    names = {x["name"] for x in projects}
    for d in donors:
        for x in d["profile"]["personal_projects"]:
            if len(projects) >= k:
                break
            if x["name"] not in names:
                projects.append(deepcopy(x))
                names.add(x["name"])
        if len(projects) >= k:
            break
    for x in projects:
        x["description"] = x["description"][:1]
        x["tech_stack"] = [t for t in x["tech_stack"] if t in p["skills"]] or x["tech_stack"][:2]
    p["personal_projects"] = projects[:k]
    rec["id"] = base["id"] + ".m"
    rec["level"] = "senior" if base["level"] in ("junior", "middle") else base["level"]
    return rec


def student(base: dict, pool: list[dict], rng: random.Random) -> dict:
    rec = deepcopy(base)
    p = rec["profile"]
    p["experience"] = []
    projects = [deepcopy(x) for x in p["personal_projects"]]
    names = {x["name"] for x in projects}
    want = rng.randint(2, 5)
    donors = [d for d in pool if d["id"] != base["id"]]
    rng.shuffle(donors)
    for d in donors:
        for x in d["profile"]["personal_projects"]:
            if len(projects) >= want:
                break
            if x["name"] not in names:
                projects.append(deepcopy(x))
                names.add(x["name"])
        if len(projects) >= want:
            break
    p["personal_projects"] = projects[:want]
    # a student has no employer awards; keep the rest of the profile as written
    p["honours"] = [h for h in p["honours"] if not any(j in h for j in ("Employee", "nhân viên", "Nhân viên"))]
    rec["id"] = base["id"] + ".s"
    rec["level"] = "junior"
    return rec


def build(profiles: Path, out: Path, n_many: int, n_student: int) -> dict:
    rng = random.Random(SEED)
    records, _ = load_profiles(profiles)
    by_lang = {lang: [r for r in records if r["lang"] == lang] for lang in ("en", "vi")}
    seniors = [r for r in records if r["level"] != "junior"]
    juniors = [r for r in records if r["level"] in ("junior", "middle")]
    rng.shuffle(seniors)
    rng.shuffle(juniors)
    made, invalid = [], 0
    for base in seniors[:n_many]:
        rec = many_jobs(base, by_lang[base["lang"]], rng)
        if validate_profile(rec):
            invalid += 1
            continue
        made.append(rec)
    taken = {r["id"] for r in seniors[:n_many]}
    for base in [r for r in juniors if r["id"] not in taken][:n_student]:
        rec = student(base, by_lang[base["lang"]], rng)
        if validate_profile(rec):
            invalid += 1
            continue
        made.append(rec)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "variants.jsonl").open("w", encoding="utf-8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in made)
    return {"many_jobs": sum(r["id"].endswith(".m") for r in made),
            "student": sum(r["id"].endswith(".s") for r in made), "invalid": invalid}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--profiles", type=Path, default=Path("data/synth_v3/profiles"))
    ap.add_argument("--out", type=Path, default=Path("data/synth_v5/profiles"))
    ap.add_argument("--many", type=int, default=70)
    ap.add_argument("--students", type=int, default=60)
    args = ap.parse_args(argv)
    print(json.dumps(build(args.profiles, args.out, args.many, args.students)))


if __name__ == "__main__":
    main()
