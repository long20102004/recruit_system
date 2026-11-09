# Feature Specification: Complete and clean the extraction output without retraining

**Created**: 2026-11-05 · **Status**: Clarified
**Input**: User: "Phần báo cáo tạm thời để lại, ưu tiên output tốt trước"; earlier: "nếu ổn rồi thì chưa cần train lại v4".

## Evidence (v3 + layout text, 19 real test CVs, variant B)
| Error group | CVs | Loss |
|---|---|---|
| A. Missing tail of the JSON: loop guard cut (CV 01, `long_string`), token cap (CV 24), model closed the object after `personal_projects` (CV 05, 599 tokens, no `skills`/`certificates`/`honours`/`languages` keys) | 3 | 40 of 73 missed skills, 7 of 10 missed projects |
| B. Extra experience entries: a project of the same output listed as a company ("E-COMMERCE WEBSITE", "Web bán hàng"), an address as company ("Vạn Phúc, Hà Đông, Hà Nội") | 5 | 8 extra companies |
| C. Junk skills: bare numbers ("815"), hobbies, long sentences | several | part of 46 extra skills |
All 73 missed skills occur verbatim in the CV text.

## Requirements
- FR-1 (A, continuation): after generation, if the output was cut (loop guard / max tokens) or is missing top-level keys that come after the last key written, run **one continuation**: keep the valid JSON prefix (cut back to the last complete element before a degenerate value), close the open structures down to the top level, append `,"<next missing key>":` and let the model continue from there (same prompt + prefilled assistant text, greedy, loop guard on). Key order = training order: personal_info, objective, education, experience, personal_projects, skills, certificates, honours, languages. Merge: keys from the continuation fill only keys that are missing or empty. At most one continuation per request; token budget = remaining context. Log counts/reason only.
- FR-2 (B): post-processing drops an experience entry whose company equals (normalised) the name of a project in the same profile, and an entry whose company is only an address (Vietnamese/English locality words: phường, quận, huyện, xã, thành phố, tỉnh, district, ward, city, province, and the names of the 63 provinces) — stats counters.
- FR-3 (C): post-processing drops skills that are only digits/punctuation, and skills longer than 8 words (sentences); measured before/after on the 19 real CVs (must not lower skills F1).
- Real CVs stay local; subagents use synthetic data only.

## Success Criteria
- SC-001: On the 19 real CVs (layout text) skills recall and project recall rise, company precision rises, no field drops > 0.01, hallucination does not rise.
- SC-002: CV 57 unchanged or better.
- SC-003: All tests pass; latency rises only for CVs that need a continuation.
