# Results: KB & Skill Linking (feature 004)

**Date**: 2026-11-04 · KB seeded from cleaned **train** labels (v1 split, 395 CVs) · measured on cleaned **val** (99 CVs, never used for seeding).

## Silver cleaning (US1)

| Split | Records | Changed | Items stripped | Items added |
|---|---:|---:|---:|---:|
| train (v1) | 395 | 21 | 92 | 7 |
| val (v1) | 99 | 3 | 11 | 2 |
| train_v2 / val_v2 / silver v2 | 450 / 80 / 530 | 0 | 0 | 0 |

20 records have group labels in `skills` (as stated in requirements.md); 4 more only in projects' `tech_stack`. The v2 files on Drive were already clean.

## KB content (US2)

| Table | Rows | Notes |
|---|---:|---|
| category | 16 | fixed set |
| skill | 646 | 21 composites dropped (link via split), 4 kept as one concept (CI/CD, BRD/SRS, TCP/IP, EF Core) |
| skill_alias | 662 | incl. 16 rare typos/variants folded at fuzzy ≥ 90 (e.g. "PostgreQl" → PostgreSQL, "REST APIs" → REST API, "Bootstrap 5" → Bootstrap) |
| skill_edge | 136 | 100 REQUIRES, 36 PART_OF (e.g. Spring Boot REQUIRES Java, Spring Data JPA PART_OF Spring Boot, Next.js REQUIRES ReactJS) |
| university / alias | 298 / 746 | 282 from the public list (244 universities/academies + 38 member schools, Wikipedia rev. 75654510) + 16 train-only schools (open set); ambiguous aliases (shared abbreviations such as "DTU", bare member names) dropped |
| job_title | 139 | |
| section_heading | 84 | from backend `SectionDictionary` |

Categories, relations and university groupings are **LLM proposals** (`reviewed=false` on all rows); Claude spot-checked frequent and random skills. Team review = edit `kb/seed/*_curated.csv`, set `reviewed=true`, rebuild, reload. Load from scratch: ~1 s, idempotent, integrity checks pass.

## Linking coverage on val (US4)

| Method | Count | Share |
|---|---:|---:|
| exact | 1,052 | 86.3% |
| normalized | 14 | 1.2% |
| split (composite, ≥ 1 part linked) | 92 | 7.6% |
| fuzzy (≥ 90) | 4 | 0.3% |
| unlinked | 57 | 4.7% |
| **linked** | **1,162 / 1,219** | **95.3%** |

- Schools: 96/99 linked (97.0%; 91.9% with the train-only list). The reference list comes from outside the dataset, so this figure is less circular than the skill coverage. Schools are never rejected for being absent (open set).
- Linking speed: 0.13 ms per CV (in-memory index). DB-backed and CSV-backed linkers give identical results (0 mismatches).
- Unlinked: soft-skill sentences ("Chịu áp lực tốt", "Eager to learn") and technologies absent from train labels (ChatGPT, JSON, Deep Learning, JupyterLab).
- Compared with the earlier measurement (exact 91.2%, normalised 0.8%, fuzzy 0.3%, unlinked 7.7%): fewer unlinked mentions, mainly thanks to composite splitting ("MySQL/PostgreSQL", "Java/Spring Boot").

**Caveat (circularity)**: the KB is seeded from the same Gemini-labelled distribution, so this shows the KB covers the dataset vocabulary, not real-world CVs. Do not claim "KB improves accuracy by X%" until variant C is measured (feature 005).
