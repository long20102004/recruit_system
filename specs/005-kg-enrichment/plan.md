# Implementation Plan: KG Enrichment (Tier 4)

**Branch**: `005-kg-enrichment` (spec dir only) | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md) | **Contract**: [contracts/extract-cv-v2.md](contracts/extract-cv-v2.md)

## Summary

Load the KB once at startup (Postgres or seed CSV) into an in-memory `KnowledgeBase` (skill linker, school alias index, skill graph). After post-processing, `enrich(profile, kb, pp_stats)` adds `skills_normalized`, `implied_skills`, `school_normalized`, `flags`. Backend DTO gains the fields. Eval gets variant C and a canonical-skill metric.

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| I. Minimal Scope | PASS | No change to extraction/postprocess; tech_stack normalisation excluded |
| II. Contracts | PASS (additive) | Documented in contracts/extract-cv-v2.md; backend DTO updated in the same feature; Jackson already ignores unknown fields |
| III. Verification | PASS | Unit tests, route tests, backend `mvn test`, eval variant C, real smoke via backend |
| IV. CV Data Security | PASS | flags carry codes/counts only; logs counts only |
| V. Maintainable | PASS | `app/kb/store.py` (loading), `app/kg/enrich.py` (pure) |

## Design

```text
ai-service/app/
├── core/config.py      # + KG_ENABLED (default true), KB_DSN (optional), KB_SEED_DIR (default ./kb/seed, resolved)
├── kb/store.py         # NEW KnowledgeBase + load_kb()
├── kg/__init__.py      # NEW
├── kg/enrich.py        # NEW enrich(profile, kb, pp_stats=None) -> dict
├── main.py             # startup: load_model(); then load_kb() when KG_ENABLED
└── api/routes.py       # call enrich after postprocess; /health adds "kb"
backend/src/main/java/recruit/demo/dto/CandidateProfile.java  # + fields
ai-service/eval/variants.py, metrics.py, report.py            # + variant C, canonical skills metric
```

### `app/kb/store.py`
```python
@dataclass
class KnowledgeBase:
    source: str                         # "postgres" | "csv"
    linker: SkillLinker
    skills: dict[int, tuple[str, str]]  # id -> (name, category)
    edges: dict[int, list[tuple[str, int]]]  # src_id -> [(rel, dst_id)]
    school_alias: dict[str, int]        # school_key -> university id
    universities: dict[int, str]        # id -> name
    def link_school(self, raw) -> tuple[int, str] | None
    @classmethod from_csv(seed_dir); @classmethod from_db(dsn)
def load_kb(dsn: str | None, seed_dir: str) -> KnowledgeBase | None:
    # try DB if dsn; on any error log type and fall back to CSV; CSV error -> None
```
Module-level `kb_state = {"kb": None}` set at startup (`app/main.py` startup: `load_model(); kb_state["kb"] = load_kb(...)` when `KG_ENABLED`).

### `app/kg/enrich.py`
- `skills_normalized`: `kb.linker.link_many(profile["skills"])` → items `{raw, id, name, category, method}` (unlinked kept with nulls; linked deduped by id).
- `implied_skills`: BFS from linked ids; for node `n`: for `(rel, dst)` in `edges[n]` where rel in (REQUIRES, PART_OF) → dst implied via `{from: name(n), rel}`; continue from dst. Exclude ids already linked; first path wins (BFS = shortest); sort by (depth, name).
- education: `school_normalized` per item.
- flags from `pp_stats` (PostprocessStats or dict): `items_removed_ungrounded + education_removed + projects_removed` → `UNGROUNDED_REMOVED` (count), `contacts_nulled` → `CONTACT_NULLED`, `experience_removed_ungrounded + experience_removed_type` → `EXPERIENCE_REMOVED`; unlinked skills count → `SKILLS_UNLINKED` (field "skills"); no email and no phone → `MISSING_CONTACT` (field "personal_info"). Only counts > 0.
- Pure; returns a new dict (deepcopy).

### Routes
After postprocess (keep `pp_stats` even when disabled → None): `if config.KG_ENABLED and kb_state["kb"]: try data = enrich(data, kb, pp_stats); log counts except: log type`. `/health` adds `"kb": {"source", "skills", "universities"}` or `null`.

### Backend DTO
Add to `CandidateProfile`: `List<NormalizedSkill> skills_normalized`, `List<ImpliedSkill> implied_skills`, `List<Flag> flags`; `Education.school_normalized` (`NormalizedRef {Integer id; String name;}`); nested static classes with `@Data @JsonIgnoreProperties(ignoreUnknown = true)`. `NormalizedSkill {String raw; Integer id; String name; String category; String method;}`, `ImpliedSkill {Integer id; String name; String category; List<Via> via;}`, `Via {String from; String rel;}`, `Flag {String code; Integer count; String field;}`. Unit test: deserialize a sample JSON with and without the new fields.

### Eval
- `variants.py`: `"C": lambda data, cv: enrich(B(data, cv), KB, stats)` with KB from `load_kb(None, "kb/seed")` (CSV for reproducibility).
- `metrics.py`: `skills_canonical` set F1 where each skill maps to `f"id:{id}"` if linked else `"raw:" + normalize(raw)`; for C use `skills_normalized` ids (unlinked raw); for A/B link with the same linker → by construction C = B on this metric unless enrichment changes skills; therefore report: `skills` (string) F1 for A/B/C and `skills_canonical` F1 for A/B/C to show the representation gain (string vs canonical), plus `implied_per_cv`, `unlinked_rate`, `kg_ms`.

## Subagent Assignment

| Task | Model |
|---|---|
| store.py + config + tests | agy `gemini-3.8-flash-high` |
| enrich.py + tests | agy `gemini-3.8-flash-high` |
| routes/main/health + tests | agy `gemini-3.8-flash-medium` |
| Java DTO + test | agy `gemini-3.8-flash-medium` |
| eval variant C + metric | agy `gemini-3.8-flash-medium` |
| README/contract docs | agy `gemini-3.8-flash-low` |
| Escalation | `openai/gpt-6.1-sol` → Claude |
