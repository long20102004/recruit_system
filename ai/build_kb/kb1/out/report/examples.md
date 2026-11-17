# Ví dụ IN–OUT

## Popular Vector DBs (pick one) (ai-engineer)

**IN (ô trên sơ đồ):** Chroma, FAISS, LanceDB, MongoDB Atlas, Pinecone, Qdrant, Supabase, Weaviate

**OUT:**

- chưa sinh quan hệ nào (nhãn chưa được phân loại)

## Relational Databases (backend)

**IN (ô trên sơ đồ):** Aurora DB, MS SQL, MariaDB, MySQL, Oracle, PostgreSQL, SQLite

**OUT:**

- `KB1_Category` "Relational Databases", `sibling_ok_suggest = false`
- `aurora db` -[IN_CATEGORY]-> `relational databases`
- `mariadb` -[IN_CATEGORY]-> `relational databases`
- `mysql` -[IN_CATEGORY]-> `relational databases`
- `oracle` -[IN_CATEGORY]-> `relational databases`
- `postgresql` -[IN_CATEGORY]-> `relational databases`
- `sql server` -[IN_CATEGORY]-> `relational databases`
- `sqlite` -[IN_CATEGORY]-> `relational databases`

## Ollama (ai-engineer)

**IN (ô trên sơ đồ):** Ollama Models, Ollama SDK

**OUT:**

- `KB1_Category` "Ollama", `sibling_ok_suggest = false`
- `ollama` -[PARENT_OF]-> `ollama models`
- `ollama` -[PARENT_OF]-> `ollama sdk`
