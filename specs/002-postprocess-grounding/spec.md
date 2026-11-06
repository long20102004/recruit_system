# Feature Specification: Post-processing & Grounding of Extracted CV Profiles (Tier 3)

**Feature Branch**: `002-postprocess-grounding` (spec directory only)
**Created**: 2026-11-04
**Status**: Draft
**Input**: requirements.md, "Pipeline mục tiêu", tier 3: grounding (company/school/project name must appear in the CV text, fuzzy ≥ 85 snap-to-source), type check for fake experience, key normalisation (honors→honours, certifications→certificates), cleaning skill group labels. Feature 001 smoke run also showed hallucinated `github_url`, `languages`, `objective`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fabricated entities are removed (Priority: P1)

As a recruiter using extracted profiles, I need companies, schools, projects and contact fields that do not exist in the CV to be removed, so that profiles never contain invented facts.

**Why this priority**: Hallucination is the main quality issue of the extractor (e.g. `github_url: "https://github.com/yourusername"`, `English – TOEFL 90` on a CV without any language section).

**Independent Test**: Feed a CV text and a model output containing invented items; the returned profile contains only items found in the CV.

**Acceptance Scenarios**:

1. **Given** an experience whose company does not appear in the CV text, **When** post-processed, **Then** that experience is removed.
2. **Given** an education entry whose school does not appear, **When** post-processed, **Then** it is removed; same for a personal project whose name does not appear.
3. **Given** `email`, `phone` or `github_url` values not present in the CV (phone compared by digits only), **When** post-processed, **Then** they become `null`.
4. **Given** certificates, honours, objective or language entries with no supporting text in the CV, **When** post-processed, **Then** they are removed (`objective` → `null`).

---

### User Story 2 - Near-miss names are corrected to the CV's spelling (Priority: P1)

As a recruiter, I need names the model misspelled by a few characters to be replaced by the exact text from the CV, rather than dropped or kept wrong.

**Independent Test**: Model output `"Cong ty FPT Softwar"` with CV containing `"Công ty FPT Software"` → output uses the CV text.

**Acceptance Scenarios**:

1. **Given** a company/school/project name whose best fuzzy match in the CV scores ≥ 85, **When** post-processed, **Then** it is replaced by the matched CV text span.
2. **Given** a name that matches exactly, **When** post-processed, **Then** it is unchanged.

---

### User Story 3 - Experience contains only real employment (Priority: P2)

**Acceptance Scenarios**:

1. **Given** an experience whose job title is empty or is "sinh viên", "student", "học viên", **When** post-processed, **Then** it is removed.
   - *Amended 2026-11-04 (first real CV, see specs/006-retrain-v2/real-cv-findings.md)*: an **empty** title no longer removes the experience (real CVs may give no title); a title not found within 200 characters before / 300 after the company in the CV is set to null instead. Student titles still remove the experience.
2. **Given** an experience whose company is a school/university and the title is a teaching role (e.g. "giảng viên", "lecturer", "trợ giảng"), **When** post-processed, **Then** it is kept.
3. **Given** an experience whose company is a school and the title is not a teaching or staff role, **When** post-processed, **Then** it is removed.
4. **Given** an experience removed for failing grounding whose company string contains the name of an existing personal project, **When** post-processed, **Then** its description bullets are appended to that project (no information loss).

---

### User Story 4 - Consistent keys, types and skills (Priority: P2)

**Acceptance Scenarios**:

1. **Given** keys `honors`, `certifications`, `projects`, **When** post-processed, **Then** they are renamed to `honours`, `certificates`, `personal_projects` and merged with existing values.
2. **Given** missing fields, **When** post-processed, **Then** all schema keys exist, with missing scalars `null` and missing lists `[]`; unknown top-level keys are dropped.
3. **Given** `description` as a string, `team_size` as `"4"`, **When** post-processed, **Then** description becomes a list of strings and team_size an integer (or `null` if not numeric).
4. **Given** skills such as `"Backend: Spring Boot"`, **When** post-processed, **Then** the group label is removed (`"Spring Boot"`); `"Spring Boot (Web, Data JPA)"` is kept as one item; duplicates (case-insensitive) are removed preserving order.

---

### User Story 5 - Operators can switch it off and measure it (Priority: P3)

**Acceptance Scenarios**:

1. **Given** a setting disabling post-processing, **When** extraction runs, **Then** the raw model output is returned exactly as before this feature (ablation "A").
2. **Given** post-processing is on, **When** it runs, **Then** the log contains only counts of removed/snapped items (no values).
3. **Given** an evaluation script, **When** it imports the post-processing function, **Then** it can apply it offline to stored model outputs (ablation "B") without running the service.

### Edge Cases

- Model output is not a dict, or a section has the wrong type (e.g. `experience` is a dict) → coerce or reset to the empty value; never crash.
- CV text contains Vietnamese diacritics while the model output omits them (or the reverse) → matching is accent- and case-insensitive.
- Very short names (< 3 characters after normalisation) → require exact containment; no fuzzy snap.
- Same company appears twice → keep both if dates differ (no dedupe across distinct roles); exact duplicate items are removed.
- Post-processing raises unexpectedly → fall back to returning the un-post-processed result and log the error type (no data).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Post-processing MUST run after JSON extraction and before the response, using the cleaned CV text as the grounding source.
- **FR-002**: Grounded entity fields (`experience.company`, `education.school`, `personal_projects.name`) MUST be kept only if found in the CV: exact (normalised) containment keeps the value, best fuzzy match ≥ 85 replaces it with the CV span, otherwise the item is removed.
- **FR-003**: Contact fields `email`, `github_url` MUST be nulled when not contained in the CV (normalised); `phone` when its digit sequence is not contained in the CV's digits. `full_name` MUST be nulled if not found with fuzzy ≥ 85.
- **FR-004**: `skills` (added 2026-11-04, whitespace-insensitive), `certificates`, `honours` string items and `objective` MUST be kept only with fuzzy ≥ 85 support in the CV; `languages` items MUST be kept only if the language name (Vietnamese or English alias) or the note appears in the CV.
- **FR-005**: Experience type check per US3 (student titles removed, teaching roles at schools kept, other school-as-company entries removed).
- **FR-006**: Removed experiences whose company string contains an existing project's name MUST have their bullets merged into that project's description.
- **FR-007**: Key normalisation, schema completion, unknown-key removal and type coercion per US4.
- **FR-008**: Skills cleaning per US4: strip leading group labels (`Label:` with label ≤ 40 characters), trim, drop empties, dedupe case-insensitively preserving first occurrence. The same cleaning applies to each project's `tech_stack`.
- **FR-009**: A setting MUST allow disabling post-processing (default: enabled).
- **FR-010**: Post-processing MUST be a pure function (profile + CV text → profile + statistics) importable without loading the model.
- **FR-011**: The response shape MUST remain `{"data": CandidateProfile}` with the same keys; no new fields are added to the response.
- **FR-012**: Logs MUST contain only counts per rule (removed, snapped, merged), never values.

### Key Entities

- **CandidateProfile**: the schema in requirements.md (`personal_info`, `objective`, `education`, `experience`, `personal_projects`, `skills`, `certificates`, `honours`, `languages`).
- **PostprocessStats**: counts per rule, e.g. `experience_removed_ungrounded`, `experience_removed_type`, `names_snapped`, `contacts_nulled`, `items_removed_ungrounded`, `bullets_merged`, `keys_renamed`, `skills_cleaned`.

## Success Criteria *(mandatory)*

- **SC-001**: On a synthetic test set of fabricated entities, 100% of fabricated companies/schools/projects/contacts are removed.
- **SC-002**: Correct (exactly present) entities are kept unchanged in 100% of test cases.
- **SC-003**: Names with ≤ 2 character errors are snapped to the CV spelling in the provided test cases.
- **SC-004**: Post-processing adds < 100 ms per CV.
- **SC-005**: With post-processing disabled, responses are byte-identical to feature 001 behaviour.

## Assumptions

- Rules and thresholds follow requirements.md (fuzzy ≥ 85 for snapping; experience type rules). Contact/objective/certificate/language grounding is an extension motivated by the observed hallucinations in feature 001's smoke run.
- Splitting `Base (a, b)` into separate skills and entity linking to a KB are out of scope (feature 004); skills are only cleaned, not normalised.
- *(Done 2026-11-04, see amendment under US3)* `job_title` proximity check (title within N characters of the company in the CV) was out of scope: higher risk of removing correct titles in 2-column PDF text; can be revisited with evaluation data (feature 003).
- `description` bullets are summaries and are not grounded.
- No backend change is needed: the response contract is unchanged.
