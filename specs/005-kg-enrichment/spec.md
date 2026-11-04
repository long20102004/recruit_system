# Feature Specification: KG Enrichment of Extracted Profiles (Tier 4)

**Feature Branch**: `005-kg-enrichment` (spec directory only)
**Created**: 2026-11-04
**Status**: Draft
**Input**: requirements.md → tier 4 "Làm giàu KG": `skills_normalized` [{raw, id, category}], `implied_skills` (via PART_OF/REQUIRES; never added to `skills`), `flags` needing confirmation; ablation variant C (+linking + KG). User decisions: additive fields inside `data` (backward compatible), backend DTO updated; universities/job titles are open sets (normalise only, never flag for absence).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Normalised skills (Priority: P1)

As Module 2 (matching CVs to job descriptions), I need every extracted skill mapped to a canonical KB skill with its category, so that "ReactJS", "React.js" and "Postgress" compare equal to "ReactJS" and "PostgreSQL".

**Acceptance Scenarios**:

1. **Given** skills ["ReactJS", "React.js", "Postgress", "Java & Spring Boot"], **When** enriched, **Then** `skills_normalized` lists each raw item with KB id, canonical name, category and linking method; composites yield one entry per linked part; duplicates by id are listed once.
2. **Given** a skill not in the KB, **When** enriched, **Then** it appears with `id = null`, `method = "unlinked"`, and the original `skills` list is unchanged.

### User Story 2 - Implied skills (Priority: P1)

As Module 2, I need skills that are implied by the listed ones (Spring Boot ⇒ Java; Spring Data JPA ⇒ Spring Boot ⇒ Java), with the reason, kept separate from what the candidate wrote.

**Acceptance Scenarios**:

1. **Given** skills ["Spring Boot"] and KB edge Spring Boot REQUIRES Java, **When** enriched, **Then** `implied_skills` contains Java with `via` = [{from: "Spring Boot", rel: "REQUIRES"}].
2. **Given** "Spring Data JPA" (PART_OF Spring Boot, which REQUIRES Java), **When** enriched, **Then** both Spring Boot and Java are implied (transitive), each with its path.
3. **Given** an implied skill already present in `skills_normalized`, **When** enriched, **Then** it is not repeated in `implied_skills`.
4. **Given** any input, **When** enriched, **Then** `skills` is never modified by implication.

### User Story 3 - Normalised school names (Priority: P2)

**Acceptance Scenarios**:

1. **Given** education school "PTIT" or "Posts and Telecommunications Institute of Technology", **When** enriched, **Then** the education item gets `school_normalized` = {id, name: "Học viện Công nghệ Bưu chính Viễn thông"}.
2. **Given** a school not in the KB (open set), **When** enriched, **Then** `school_normalized` is null and **no flag** is raised for it.

### User Story 4 - Flags for human confirmation (Priority: P2)

As a recruiter, I need short machine-readable warnings telling me which parts of the profile need checking.

**Acceptance Scenarios**:

1. **Given** post-processing removed or nulled values, **When** enriched, **Then** flags report them by code and count (e.g. `UNGROUNDED_REMOVED`, `CONTACT_NULLED`, `EXPERIENCE_REMOVED`), without echoing the removed values.
2. **Given** unlinked skills, **When** enriched, **Then** a `SKILLS_UNLINKED` flag gives their count.
3. **Given** a profile without email and phone, **When** enriched, **Then** a `MISSING_CONTACT` flag is raised.
4. **Given** a school or job title absent from the KB, **When** enriched, **Then** no flag is raised.

### User Story 5 - Measure variant C (Priority: P2)

**Acceptance Scenarios**:

1. **Given** the cached predictions of feature 003, **When** the report is regenerated with variant C, **Then** it shows canonical-skill F1 (pred vs gold both linked to KB ids) for B and C, implied-skill statistics, and KG latency — without re-running the model.

### Edge Cases

- KB database unavailable at startup → service loads the versioned seed files instead and reports the KB source in `/health`; if both fail, enrichment is skipped (fields absent), extraction still works.
- Enrichment raises → response without enrichment fields, error type logged.
- Implication cycles cannot occur (KB load rejects cycles); traversal still guards against revisits.
- Empty skills / education → empty `skills_normalized`, `implied_skills`; no crash.

## Requirements *(mandatory)*

- **FR-001**: Response `data` MAY contain new keys `skills_normalized`, `implied_skills`, `flags`, and each education item `school_normalized`; all existing keys and value shapes stay unchanged.
- **FR-002**: `skills_normalized` item = {raw, id, name, category, method}; order follows `skills`; duplicate ids collapsed (first raw kept).
- **FR-003**: `implied_skills` item = {id, name, category, via: [{from, rel}]}; follows REQUIRES transitively and PART_OF upward (A PART_OF B ⇒ B implied), then REQUIRES of those; excludes ids in `skills_normalized`; deterministic order.
- **FR-004**: `school_normalized` = {id, name} or null.
- **FR-005**: `flags` item = {code, count?, field?}; codes: `UNGROUNDED_REMOVED`, `CONTACT_NULLED`, `EXPERIENCE_REMOVED`, `SKILLS_UNLINKED`, `MISSING_CONTACT`; never contains CV values; never raised for KB absence of schools/titles.
- **FR-006**: KB source: PostgreSQL via `KB_DSN` when set and reachable, else seed CSVs (`KB_SEED_DIR`, default `kb/seed`); loaded once at startup; `/health` reports `kb` = {source, skills, universities}.
- **FR-007**: `KG_ENABLED` (default true) switches enrichment off (responses identical to feature 002 behaviour).
- **FR-008**: Backend DTO `CandidateProfile` exposes the new fields so `/api/v1/cv/analyze*` return them; existing backend behaviour unchanged.
- **FR-009**: Evaluation variant C and canonical-skill metric per US5.
- **FR-010**: Logs contain counts only.

## Success Criteria *(mandatory)*

- **SC-001**: Enrichment adds < 20 ms per CV.
- **SC-002**: Existing consumers parse responses unchanged (backend tests pass; fields additive).
- **SC-003**: On val, canonical-skill F1 for C ≥ B's, with breakdown reported.
- **SC-004**: 0 CV values inside `flags`.

## Assumptions

- Project `tech_stack` items are not normalised in this feature (skills only), to keep the response small; can be added later.
- `flags` replace no existing behaviour; they are advisory.
- Backend rule-based branch (`/extract-rule-based`) does not produce the new fields (they stay null there).
