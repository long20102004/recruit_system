# Feature Specification: Knowledge Base (PostgreSQL) & Skill Entity Linking

**Feature Branch**: `004-kb-skill-linking` (spec directory only)
**Created**: 2026-11-04
**Status**: Draft
**Input**: requirements.md → "KB / KG (đề xuất, CHƯA cài đặt)" and backlog items 1–2: clean the 20 silver records with group labels in skills; seed a KB from silver labels (skills, aliases, categories, universities, job titles, section headings, skill relations); entity-linking function (key normalisation, alias grouping, fuzzy ≥ 90). User decision: KB in PostgreSQL from the start.

## Context (verified 2026-11-04)

- Train gold: 4,793 skill mentions, 616 distinct surface forms, ~568 canonical keys, 39 keys with ≥ 2 surface forms (e.g. React / ReactJS / React.js).
- 79 mentions with a group label prefix ("Backend: …", "Tools: …") in exactly 20 records (train + val), matching requirements.md.
- Composite items exist: "Java & Spring Boot", "Git/GitHub", "Node.js (Express)".
- A `postgres:16` container of another project already listens on 5432; the backend has no datasource yet.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean silver labels (Priority: P1)

As the team preparing retraining and KB seeding, I need the 20 silver records whose skills contain group labels to be cleaned reproducibly, so that the KB and any future training use clean skill names.

**Independent Test**: Run the cleaning command; it reports 20 affected records and writes cleaned copies of each split; re-running produces identical output.

**Acceptance Scenarios**:

1. **Given** a skill "Backend: Spring Boot, Node.js", **When** cleaned, **Then** it becomes "Spring Boot" and "Node.js".
2. **Given** a record without group labels, **When** cleaned, **Then** it is byte-identical to the input.
3. **Given** the cleaning run, **When** finished, **Then** a summary shows counts only (records changed, items split/stripped) per split.

### User Story 2 - KB in PostgreSQL seeded from the data (Priority: P1)

As the team, I need a PostgreSQL knowledge base holding canonical skills with aliases and categories, skill relations (part-of, requires), universities with aliases, job titles and section headings, created and loaded with one command each, so that linking, the KG enrichment (feature 005) and Module 2 share one source of truth.

**Acceptance Scenarios**:

1. **Given** a machine with Docker, **When** the KB database is started, **Then** it runs on its own port without touching other local PostgreSQL instances.
2. **Given** the seed files, **When** loaded, **Then** the DB contains every canonical skill exactly once, every alias maps to one skill, every skill has a category, and relations reference existing skills; loading twice yields the same content.
3. **Given** the seed files in the repository, **When** reviewed, **Then** they are human-readable tables with a "reviewed" marker, so manual review is tracked in version control.
4. **Given** the KB, **When** queried for "Spring Data JPA", **Then** a PART_OF relation to "Spring" (or "Spring Boot" family) exists, and "Spring Boot" REQUIRES "Java".

### User Story 3 - Link raw skills to KB entities (Priority: P1)

As the extraction pipeline, I need a function that maps a raw skill string to KB skills with the method used, so that duplicates and spelling variants collapse to one canonical skill.

**Acceptance Scenarios**:

1. **Given** "ReactJS", "React.js", "react", **When** linked, **Then** all map to the same canonical skill.
2. **Given** "Tailwind-CSS", **When** linked, **Then** it maps to "Tailwind CSS" via normalisation.
3. **Given** "Postgress", **When** linked, **Then** it maps to "PostgreSQL" via fuzzy matching (≥ 90) and reports the score.
4. **Given** "Java & Spring Boot" or "Git/GitHub" with no whole-string match, **When** linked, **Then** it is split and each part linked; a whole-string alias always wins over splitting ("CI/CD" stays one skill).
5. **Given** a soft-skill sentence or unknown technology, **When** linked, **Then** it is reported as unlinked (no forced match).
6. **Given** the linker, **When** used without a database (tests, offline evaluation), **Then** it can be built from the seed files with identical results.

### User Story 4 - Measure linking coverage (Priority: P2)

As the team writing Ch3, I need a reproducible measurement of linking on validation CVs (never used for seeding), reporting exact / normalised / fuzzy / split / unlinked shares, so we can compare with the earlier numbers (exact 91.2%, normalised 0.8%, fuzzy 0.3%, unlinked 7.7%) and state the circularity caveat.

**Acceptance Scenarios**:

1. **Given** the val split gold skills, **When** measured, **Then** a report with counts and shares per method is written (aggregates only).
2. **Given** university names in val gold, **When** measured, **Then** the share linked to KB universities is reported.

### Edge Cases

- Alias collision (two canonical skills claim the same alias key) → seed build fails with a clear message listing the key.
- Very short skills ("C", "R", "Go") → exact alias only, never fuzzy.
- Case-sensitive distinctions that normalise identically ("C#" vs "C", "C++") → keys preserve `+` and `#`.
- Relations cycles (A PART_OF B PART_OF A) → rejected at load time.
- Database unavailable → loader exits non-zero with a clear message; linker from seed files still works.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cleaning command for silver splits (group-label strip + top-level split of skills) writing cleaned copies next to the originals in the git-ignored data folder, with a counts-only summary.
- **FR-002**: KB schema: categories, skills (canonical name, category, reviewed flag), skill aliases (normalised key → skill), skill relations (`PART_OF`, `REQUIRES`) between skills, universities + aliases, job titles, section headings (heading → section). Skill → category is the `BELONGS_TO` relation of requirements.md. `TYPICALLY_USES` (job title → skill) table exists but is seeded in Module 2.
- **FR-003**: Seed build command derives skills/aliases from cleaned **train** gold only; categories and relations come from a curated file (proposed automatically, reviewed by a human), merged deterministically.
- **FR-004**: Universities seed from train gold schools grouped by normalised key, with known abbreviations as aliases; job titles from train gold titles; section headings from the backend's section dictionary.
- **FR-005**: Load command applies the schema and loads seeds idempotently in one transaction; validates uniqueness, references and acyclicity.
- **FR-006**: Linker per US3 with methods `exact`, `normalized`, `fuzzy` (≥ 90, only for keys ≥ 4 characters), `split`, `unlinked`; buildable from DB or seed files.
- **FR-007**: Measurement command per US4.
- **FR-008**: The local KB database MUST run on a dedicated port (default 5433) via a compose file; credentials come from an environment file that is not committed (an example file is committed).
- **FR-009**: No change to the extraction API response in this feature (KG enrichment is feature 005).

### Key Entities

Category, Skill, SkillAlias, SkillEdge(src, rel, dst), University, UniversityAlias, JobTitle, SectionHeading, Link(raw, skill, method, score).

## Success Criteria *(mandatory)*

- **SC-001**: Cleaning reports exactly the affected records (expected 20) and is reproducible.
- **SC-002**: Loading the KB from scratch takes < 1 minute and passes all integrity checks.
- **SC-003**: On val gold skills, linked share (exact + normalised + fuzzy + split) ≥ 90%, with the per-method breakdown reported.
- **SC-004**: Linking one CV's skills takes < 10 ms after the index is built.
- **SC-005**: 100% of seed skills have a category; 100% are marked reviewed or listed in a review backlog.

## Assumptions

- Silver gold labels are the seed source; the KB therefore covers the dataset's vocabulary well, which is circular for evaluation on the same distribution — the measurement report states this caveat (requirements.md).
- Categories and relations are proposed by an LLM subagent from the canonical skill list (skill names are not personal data) and spot-checked by Claude; full human review by the team is tracked by the `reviewed` flag.
- Company KB is out of scope (open set; grounding already enforces "must appear in CV").
- Neo4j is optional and out of scope.
- The backend is not connected to the KB in this feature; wiring is done where it is consumed (feature 005 in ai-service; Module 2 in backend).
