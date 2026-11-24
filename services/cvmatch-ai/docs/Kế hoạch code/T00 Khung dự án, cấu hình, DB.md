# T00 · Khung dự án, cấu hình có phiên bản, schema database

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `00` (mục 3.4 bộ khoá phiên bản) · `03` (toàn bộ, đặc biệt "Các bảng", "Dữ liệu đầu ra") · `04`, `05` (mục "Kết quả và nơi lưu" của từng bước, để lấy cột) · `06` mục 3 · `07` mục 6 · `11` mục 1 (bảng tham số).

## Mục tiêu

Dựng bộ khung mà mọi phần sau dùng chung: project Python, file cấu hình, kết nối DB, và **toàn bộ schema** Postgres. Chưa có logic xử lý nào.

## Làm

1. **Project** `services/cvmatch-ai/` theo cây thư mục ở file 00 (tạo package rỗng có `__init__.py`). `pyproject.toml` với: `pydantic>=2`, `pyyaml`, `psycopg[binary]>=3`, `pgvector`, `numpy`, `pytest`. (Các thư viện nặng như torch, bm25s, pyvi để phần dùng tới tự thêm.)
2. **docker-compose.yml**: `pgvector/pgvector:pg16`, volume, `.env.example` (`CVMATCH_DB_URL`, `CVMATCH_HMAC_KEY`, `CVMATCH_DEVICE`).
3. **`core/config.py`**:
   - Đọc các file YAML trong `config/` thành model pydantic có kiểm kiểu (`PrepConfig`, `RetrieveConfig`, `RerankConfig`, `BertScoreConfig`, `ExplainConfig`).
   - Điền **đủ mọi tham số** ở thiết kế 11 mục 1.1–1.4 với giá trị mặc định đúng như bảng (giữ chú thích "ƯL"/"đã test" trong YAML).
   - Hàm sinh khoá: `pipeline_version` (vd `prep-1.0`), `rerank_config_version`, `bertscore_config` theo đúng mẫu `bge-m3@5617a9f61b/L24/noidf/norescale/2048/mask1` (có cờ chuẩn bị đầu vào).
   - `config_hash()` để ghi vào `match_run.config_json` / `rerank_run`.
4. **`config/patterns/`**: file danh sách (mỗi dòng một mẫu) cho `negation`, `coursework`, `generic_resp`, `injection` (thiết kế 08 mục 6), và `locations.yaml` (alias → mã tỉnh, gồm `remote`). Điền danh sách khởi đầu từ ví dụ trong thiết kế 04 A4/A7, 05 B6.
5. **`core/db.py`**: pool kết nối, context manager `transaction()`, đăng ký kiểu `halfvec` của pgvector, helper `executemany`.
6. **Migrations** (`migrations/*.sql` + lệnh `cvmatch db migrate` chạy theo thứ tự, ghi bảng `schema_migrations`):
   - `001_kb_snapshot.sql`: `skill_ontology`, `role_title_map`, `role_distance`, `major_group`, `ambiguous_aliases` (thiết kế 02 mục 8), khoá gồm `ontology_version`.
   - `002_cv.sql`: `cv`, `cv_meta`, `cv_experience`, `cv_education`, `cv_skill`, `cv_bullet`, `cv_vector`, `cv_bullet_vector`, `cv_bm25_doc` — cột và kiểu đúng như mục "Kết quả và nơi lưu" của A1–A11. Index trên `cv.content_hash`, `cv.candidate_key`, `(status, is_latest)`.
   - `003_jd.sql`: `jd` (PK `(jd_id, version)`), `jd_meta`, `jd_skill`, `jd_responsibility`, `jd_requirement_item`, `jd_vector`.
   - `004_common.sql`: `unknown_skill` (unique `text`), `ingest_log`.
   - `005_retrieve.sql`: `match_run`, `match_result` (thiết kế 06 mục 3).
   - `006_rerank.sql`: `rerank_run`, `rerank_feature`, `rerank_result`, `bertscore_token_cache`, `bertscore_pair_cache` (thiết kế 07 mục 6).
   - Không tạo index HNSW trên cột vector (thiết kế 04 A10).
   - Mọi bảng chính có 3 cột phiên bản `ontology_version`, `pipeline_version`, `embed_model`.
7. **`core/contracts.py`**: khai báo pydantic (chưa dùng) cho `RerankRequest`, `FeatureRow`, `FinalItem` đúng thiết kế 07 mục 6 và 08 mục 1, để các phần sau dùng chung.

## Không làm

Logic tiền xử lý, encoder, KB matcher.

## Tiêu chí xong

- `docker compose up` + `cvmatch db migrate` tạo đủ bảng trên DB rỗng; chạy lại lần hai không lỗi.
- Test: nạp config mặc định, kiểm vài giá trị (`weights` cộng đúng 1,00; `bertscore_config` ra đúng chuỗi mẫu).
- Test: tạo bảng xong, liệt kê bảng khớp danh sách 17 + 5 + 2 + 5.
- Bảng đối chiếu (trong "Ghi chú bàn giao"): mỗi bảng ↔ mục thiết kế đã lấy cột.

## Ghi chú bàn giao

**Trạng thái: xong (15/11/2026).**

- **Env:** conda `cvmatch` (clone từ `module2`, Python 3.11, đã có torch/transformers). Cài: `pip install -e ".[dev]"` trong `services/cvmatch-ai`.
- **DB:** `docker compose up -d` (Postgres 16 + pgvector, cổng **5433**), `python -m cvmatch.cli db migrate`, `db status`. URL mặc định trong `.env.example`.
- **Config:** `config/active.yaml` chọn file theo tầng; thêm `models.yaml` (model embedding dense) tách khỏi `bertscore.yaml` để đổi model Retrieve không đổi backbone BERTScore. `load_config(overrides=...)` dùng cho ablation. `python -m cvmatch.cli config show` in bộ khoá phiên bản + `config_hash`.
- **Lệch so với thiết kế (cần biết):**
  - `bertscore_config` thêm đuôi `/alias1/text_raw/fp32` sau mẫu `…/2048/mask1`, vì cờ đổi alias, loại đầu vào và dtype đều làm đổi embedding → phải nằm trong khoá cache.
  - `role_title_map` một bảng có cột `kind ∈ {title, level}`; thêm bảng `kb_version` (manifest, cờ `include_candidate`) và cột `skill_ontology.status` (theo Q-3).
  - `jd.status` thêm `expired`; `ingest_log.status` thêm `deleted`; `unknown_skill` thêm `last_seen`, `sources`; `match_run`/`rerank_run` thêm `config_hash`, `n_pool`/`timings_json`.
  - `bertscore_token_cache` PK là `(text_hash, bertscore_config)`.
  - `level_from_years` (suy cấp bậc từ số năm, điểm mở 9) đặt giá trị khởi đầu (ƯL) trong `prep-1.0.yaml`.
- **Bảng ↔ thiết kế:** KB 5 bảng ← 02 mục 8; `cv*` ← 04 A1–A11; `jd*` ← 05 B1–B8; `unknown_skill`, `ingest_log` ← 03; `match_*` ← 06 mục 3; `rerank_*`, cache ← 07 mục 6.
- **Test:** `python -m pytest -q` (test `db` tự tạo database tạm và tự skip nếu không có Postgres).
