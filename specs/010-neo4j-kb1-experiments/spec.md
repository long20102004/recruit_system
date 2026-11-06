# Feature Specification: Neo4j KG, KB1 from books, model comparison, final report

**Created**: 2026-11-05 · **Status**: Clarified
**Input**: User: "Bạn triển khai nốt các phần việc còn lại để hoàn thiện báo cáo, chạy lại service AI trên colab để test output sau khi bổ sung KB, KG". Remaining items = report appendix A (supervisor requirements: "code load file pdf chuyển sang Neo4j gọi KB1, code chuyển các link sang Neo4j gọi KB2, code gộp KB1, KB2 thành KB; cập nhật KB"; KB from several sources + PDF books; compare models on several datasets; rich visuals).

## Clarifications (2026-11-05)
- Neo4j becomes the **main KG store**: KB1 (books) and KB2 (external linked sources, feature 009 seed) are loaded into Neo4j and merged into one KB; the AI service reads the KB from Neo4j when `NEO4J_URI` is set, CSV seed stays the fallback (Colab, tests). The PostgreSQL KB is no longer the primary store.
- Books chosen by Claude, open licences: *Pro Git* 2nd ed. (S. Chacon, B. Straub; CC BY-NC-SA 3.0; official PDF release) and *Think Python* 2nd ed. (A. Downey; CC BY-NC 3.0; official PDF).
- Extra experiment model: Qwen3-1.7B base without fine-tuning (zero-shot, prompt v3). RAG variant not in scope.

## User Scenarios

### US1 — KB1 from PDF books (P1)
`python -m kb.books` downloads the PDFs (not committed; SHA-256 + URL + licence in MANIFEST), reads the outline (book → chapter → section with pages) and the text of each section, and writes `kb/sources/kb1_books.json` holding **facts only, no copied prose**: book metadata, section tree (title, level, page), and per section the KB2 skills it mentions (KB surface matching, counts). Derived relations: `MENTIONS` (section → skill), `RELATED_TO` (skill ↔ skill, co-mentioned in ≥ N sections, weight = sections, source = book).

KB1 snapshot schema:
```json
{"books": [{"id": "progit", "title": "...", "authors": [...], "edition": "2", "licence": "CC BY-NC-SA 3.0",
            "url": "...", "sha256": "...",
            "sections": [{"id": "progit:3.6", "title": "Rebasing", "level": 2, "page": 99, "parent": "progit:3",
                          "mentions": {"Git": 12, "GitHub": 1}}]}],
 "related": [{"a": "Git", "b": "GitHub", "sections": 7, "source": "progit"}]}
```
(skill names = KB2 canonical names.)

### US2 — Neo4j as the KG store (P1)
- `infra/kg/docker-compose.yml`: `neo4j:5.26-community`, bound to 127.0.0.1 (7474 browser, 7687 bolt), password from `infra/kg/.env` (git-ignored).
- `python -m kb.neo4j_load`: (1) **KB2**: `Skill{id,name,category,source}`, `Alias{key,surface,source}-[:ALIAS_OF]->Skill`, `Category`, `(Skill)-[:IN_CATEGORY]->`, `(Skill)-[:REQUIRES|PART_OF {source}]->(Skill)`, `University`, `UniversityAlias`, `JobTitle`; (2) **KB1**: `Book`, `Section` (`HAS_SECTION` tree), `(Section)-[:MENTIONS {count}]->(Skill)`; (3) **merge KB1 + KB2**: `(Skill)-[:RELATED_TO {weight, source}]-(Skill)` from KB1, `Section` titles that link to a KB2 skill get `(Section)-[:ABOUT]->(Skill)`; every node/edge keeps `source`. Idempotent (MERGE + constraints), prints counts.
- AI service: `KnowledgeBase.from_neo4j(uri, user, password)` builds the same in-memory structures (skills, aliases, edges incl. RELATED_TO, universities); `load_kb` order Neo4j → CSV. `include=kg` exposes `related_skills` (from KB1) next to `implied_skills`.
- Updating the KB = rerun fetch/books → build → neo4j_load (documented).

### US3 — Model comparison (P1)
5 models × 4 datasets: rule-based (backend), Qwen3-1.7B base zero-shot, v1, v2, v3 (GGUF Q4_K_M, llama.cpp, same serving code incl. feature 008) on val (99), val_swap (99), dev_v3 (45 generated real-layout CVs), test_real (20). `eval/run_models.py` runs one GGUF over splits through the serving pipeline; `ai-service/eval_models_colab.ipynb` runs all LLMs on a Colab T4 and writes predictions to Drive; scoring locally with the feature 003 harness (variant B).

### US4 — Report (P1)
`docs/Module1_Pipeline_Finetune_KB_KG.docx` updated: Neo4j/KB1/KB2/merge chapter with code and Cypher, KG figure exported from the real graph, F1 charts (5 models × 4 datasets), Colab output examples with `include=kg`, appendix A updated.

## Success Criteria
- SC-001: Neo4j holds KB1 + KB2 + merge with source on every node/edge; service starts from Neo4j and from CSV; all tests pass.
- SC-002: KB1 snapshot contains no copied paragraphs (titles, pages, counts only).
- SC-003: Comparison table complete for the models/datasets that ran; missing cells explained.

## Constraints
- New dependency `neo4j` (Python driver) — required by the clarified design. PDFs read with poppler `pdftotext` (already installed), no new PDF library.
- No real CV sent to external services; Colab runs use the user's Drive as before.
