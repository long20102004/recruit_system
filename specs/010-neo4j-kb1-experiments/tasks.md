# Tasks: Neo4j KG, KB1 from books, model comparison (feature 010)

- [ ] T001 [P] [US1] `kb/books.py` (download Pro Git + Think Python PDFs to a git-ignored cache, outline + section text via pdftotext, KB2 skill mentions, RELATED_TO), `kb/sources/kb1_books.json`, MANIFEST entries, tests `tests/kb/test_books.py` — *ChatGPT gpt-6.1-sol*
- [ ] T002 [P] [US2] `infra/kg/` (compose, .env.example, .gitignore), `kb/neo4j_load.py`, `KnowledgeBase.from_neo4j` + `load_kb` order + config `NEO4J_*`, `related_skills` in `include=kg`, requirements, tests with a fake driver — *Gemini gemini-3.8-flash-high*
- [x] T003 [P] [US3] `eval/run_models.py` + `eval_models_colab.ipynb` — *Claude* (smoke-tested on 1 dev CV, CPU)
- [ ] T004 [US2] Start Neo4j, load KB1+KB2, verify counts, service from Neo4j, export KG figure — *Claude, after T001/T002*
- [ ] T005 [US3] Rule-based on dev_v3/test_real (backend runner); score all predictions; charts — *Claude, after Colab runs*
- [ ] T006 [US4] Report update; Colab output test with `include=kg` — *Claude*
