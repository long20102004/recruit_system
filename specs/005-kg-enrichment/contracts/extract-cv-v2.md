# Contract: `POST /api/v1/extract-cv` response, additive fields (feature 005)

All feature 001/002 fields and statuses are unchanged. When KG enrichment is enabled and the KB is loaded, `data` additionally contains:

```json
{
  "data": {
    "...": "existing CandidateProfile keys",
    "education": [{"school": "PTIT", "...": "...", "school_normalized": {"id": 187, "name": "Học viện Công nghệ Bưu chính Viễn thông"}}],
    "skills_normalized": [
      {"raw": "React.js", "id": 452, "name": "ReactJS", "category": "Frontend", "method": "exact"},
      {"raw": "Postgress", "id": 431, "name": "PostgreSQL", "category": "Database", "method": "fuzzy"},
      {"raw": "Chịu áp lực tốt", "id": null, "name": null, "category": null, "method": "unlinked"}
    ],
    "implied_skills": [
      {"id": 300, "name": "Java", "category": "Programming Language", "via": [{"from": "Spring Boot", "rel": "REQUIRES"}]}
    ],
    "flags": [
      {"code": "UNGROUNDED_REMOVED", "count": 2, "field": null},
      {"code": "SKILLS_UNLINKED", "count": 1, "field": "skills"}
    ]
  }
}
```

- `method` ∈ `exact | normalized | split | fuzzy | unlinked`.
- `implied_skills` never overlaps `skills_normalized` ids and is never merged into `skills`.
- `school_normalized` is `null` when the school is not in the KB (open set; not an error).
- `flags.code` ∈ `UNGROUNDED_REMOVED | CONTACT_NULLED | EXPERIENCE_REMOVED | SKILLS_UNLINKED | MISSING_CONTACT`; flags never contain CV values.
- Ids are KB ids (`skill.id`, `university.id`) of the loaded KB; stable only for a given seed build.

`GET /health` adds `"kb": {"source": "postgres" | "csv", "skills": int, "universities": int}` or `null`.

Consumer: backend `CandidateProfile` DTO exposes the same snake_case fields.
