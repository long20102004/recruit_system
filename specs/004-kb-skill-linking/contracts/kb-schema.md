# Contract: KB schema (PostgreSQL, `recruit_kb`)

Consumers: ai-service linker/KG enrichment (feature 005, read-only), backend Module 2 (read-only). Writer: `python -m kb.load` only.

| Table | Columns | Constraints |
|---|---|---|
| `category` | `id SERIAL PK`, `name TEXT UNIQUE NOT NULL` | |
| `skill` | `id INT PK`, `name TEXT UNIQUE NOT NULL`, `category_id INT NOT NULL → category`, `reviewed BOOL NOT NULL DEFAULT false` | `skill.category_id` = BELONGS_TO |
| `skill_alias` | `alias_key TEXT PK`, `skill_id INT NOT NULL → skill`, `surface TEXT NOT NULL` | one key → one skill |
| `skill_edge` | `src_id INT → skill`, `rel TEXT`, `dst_id INT → skill`, PK(src_id, rel, dst_id) | `rel IN ('PART_OF','REQUIRES')`, `src_id <> dst_id`, acyclic per rel (checked at load) |
| `university` | `id INT PK`, `name TEXT UNIQUE NOT NULL`, `reviewed BOOL` | |
| `university_alias` | `alias_key TEXT PK`, `university_id INT → university`, `surface TEXT` | |
| `job_title` | `id INT PK`, `name TEXT UNIQUE NOT NULL`, `alias_key TEXT UNIQUE NOT NULL` | |
| `job_title_skill` | `job_title_id → job_title`, `skill_id → skill`, `weight REAL` | TYPICALLY_USES; empty until Module 2 |
| `section_heading` | `heading TEXT PK`, `section TEXT NOT NULL` | `section` ∈ backend `CvSection` names |

Keys: `skill_key` / `school_key` defined in `ai-service/app/kb/keys.py`; consumers MUST use the same functions (or port them identically) to look up aliases.

Semantics: `A PART_OF B` = A is a component/sub-library of B (Spring Data JPA PART_OF Spring). `A REQUIRES B` = using A implies knowing B (Spring Boot REQUIRES Java). Implied skills (005) follow PART_OF upward and REQUIRES transitively; they are never merged into the CV's `skills`.

Open sets: `university` and `job_title` are normalisation dictionaries, not whitelists. Consumers MUST NOT reject or flag a school/title because it is absent from the KB; absence means "no normalised name" only.
