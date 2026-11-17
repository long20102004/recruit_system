# 00 · Kế hoạch code module Match CV ↔ JD

> Căn cứ: bộ thiết kế 2.0 trong `ai/docs/Thiết kế/` (00–12). Folder `ai/matchCV/` là code cũ, **không dùng, không đọc, không sửa**.
> Mỗi file `Txx` trong thư mục này là **một phần việc giao cho một agent**. Làm tuần tự theo bảng ở mục 3; mỗi phần có tiêu chí xong riêng.

---

## 1. Kiến trúc code

Một project Python duy nhất `ai/cvmatch/`, chia **package con theo tầng** của thiết kế. Các package chỉ nói chuyện với nhau qua **PostgreSQL** và **hợp đồng dữ liệu** (`core/contracts.py`), không import chéo.

```
ai/cvmatch/
├── pyproject.toml              # package "cvmatch", Python 3.11
├── config/                     # file cấu hình CÓ PHIÊN BẢN (file 11 của thiết kế)
│   ├── prep-1.0.yaml           #   tiền xử lý: ev, w_imp, bullet.min_words, danh sách mẫu...
│   ├── retrieve-1.0.yaml       #   K, views, normalization, fusion, bm25...
│   ├── rr-1.0.yaml             #   rerank: weights, calib, gate, missing policy...
│   ├── bertscore.yaml          #   model, layer, idf, max_len, mask_numbers...
│   ├── explain-1.0.yaml
│   └── patterns/               #   negation.txt, coursework.txt, generic_resp.txt, locations.yaml
├── migrations/                 # 001_kb_snapshot.sql, 002_cv.sql, 003_jd.sql, 004_common.sql, 005_retrieve.sql, 006_rerank.sql
├── docker-compose.yml          # postgres 16 + pgvector
├── src/cvmatch/
│   ├── core/                   # DÙNG CHUNG, không phụ thuộc package nào khác
│   │   ├── config.py           #   đọc YAML → pydantic, sinh khoá phiên bản
│   │   ├── db.py               #   kết nối psycopg3 + pgvector, transaction helper
│   │   ├── contracts.py        #   RerankRequest, FeatureRow, FinalItem... (pydantic)
│   │   ├── text/               #   normalize (A4 = B2), protected tokens, diacritics, segment, bm25 tokens
│   │   ├── kb/                 #   load snapshot, SkillMatcher, role/level/major lookup, rel(), M
│   │   └── models/             #   nạp bge-m3 MỘT lần: dense/sparse encoder + token embeddings
│   ├── ingest/                 # TẦNG 0 — nạp CV (Luồng A) và JD (Luồng B)
│   │   ├── cv/                 #   a01_schema … a11_write
│   │   ├── jd/                 #   b01_schema … b08_write
│   │   └── cli.py              #   `cvmatch ingest cv|jd <path>`, `cvmatch reprocess --from A5`
│   ├── retrieve/               # TẦNG 1 — chỉ ĐỌC bảng tiền xử lý, ghi match_run/match_result
│   │   ├── index.py            #   dựng cấu trúc RAM từ Postgres
│   │   ├── views.py            #   dense, bm25, skill, resp
│   │   ├── fusion.py           #   minmax, rrf, score_sum, tie-break
│   │   ├── flow_c.py           #   JD → CV
│   │   └── flow_d.py           #   CV → JD (P3)
│   ├── rerank/                 # TẦNG 2
│   │   ├── bertscore/          #   prepare (alias, che số), token cache, R_ij + alignment
│   │   ├── features/           #   a1_a2.py, b4_b5.py, b1_b2_b3.py, c1.py
│   │   ├── scoring.py          #   missing policy, gate, S_raw, score, xếp hạng
│   │   └── run.py              #   RR1–RR6
│   ├── explain/                # TẦNG 3 — template (P1), llm (P2)
│   ├── api/                    # FastAPI cho backend Java gọi
│   └── evaluation/             # golden test, độ phủ Module 1, metric, ablation, bất biến
└── tests/
    ├── fixtures/               # KB mini, CV/JD JSON mẫu, golden pairs
    └── unit/ integration/ gpu/ # test GPU đánh dấu @pytest.mark.gpu
```

**Quy tắc phụ thuộc (bắt buộc):**

```
core  ◄── ingest
core  ◄── retrieve
core  ◄── rerank  ◄── explain (chỉ dùng contracts)
mọi thứ ◄── api, evaluation
```

- `ingest` không import `retrieve`/`rerank`; `retrieve` không import `ingest`. Dữ liệu đi qua Postgres.
- Hàm chuẩn hoá, SkillMatcher, encoder **chỉ có một bản** trong `core` (thiết kế: "cùng hàm A4 = B2, cùng bản chụp KB").
- Mọi tham số (ƯL) đọc từ `config/`, không viết cứng. Mỗi bản ghi mang bộ khoá phiên bản (thiết kế 00 mục 3.4).

**KB:** việc xuất bản chụp từ Neo4j làm trong `ai/build_kb/` (đúng phạm vi đã quy định cho KB), ra **file** snapshot. `cvmatch` chỉ có lệnh nạp file snapshot vào 5 bảng Postgres. Hai bên không phụ thuộc code của nhau.

---

## 2. Quy tắc chung cho mọi agent

1. Đọc `00 Tổng quan kế hoạch.md` (file này) và file `Txx` được giao, rồi đọc các file thiết kế mà `Txx` chỉ ra. Không đọc `ai/matchCV/`.
2. Chỉ làm đúng phạm vi của `Txx`. Thấy thiếu thứ của phần khác thì ghi vào mục "Ghi chú bàn giao" cuối file `Txx`, không tự làm.
3. Tên bảng, cột, bước, feature **đúng như thiết kế** (`ev`, `w_imp`, `text_raw`, `f_A1`…).
4. Mỗi hàm xử lý là hàm thuần khi có thể; test bằng `pytest`. Test không cần GPU phải chạy được với encoder giả (`FakeEncoder`).
5. Thư viện mới ghi vào `pyproject.toml`. Chạy bằng conda env riêng của module (đề xuất tên `cvmatch`, chốt ở T00).
6. Xong việc: cập nhật mục "Trạng thái" ở bảng dưới và viết "Ghi chú bàn giao" (đã làm gì, chỗ nào còn giả định, lệnh chạy test).

---

## 3. Danh sách phần việc

Cột **Giai đoạn** theo lộ trình P0–P4 của thiết kế (file 11 mục 2).

| # | Phần việc | Package | Phụ thuộc | Giai đoạn | Trạng thái |
| --- | --- | --- | --- | --- | --- |
| [[T00 Khung dự án, cấu hình, DB]] | khung project, config có phiên bản, migrations toàn bộ bảng, docker Postgres | `core`, `migrations` | — | P1 | ✅ 15/11 |
| [[T01 Xuất bản chụp KB]] | cấp `skill_id`, xuất 5 bảng snapshot ra file; lệnh nạp snapshot vào Postgres | `build_kb` + `core/kb` | T00 | P0 | ✅ 16/11 |
| [[T02 Core - chuẩn hoá văn bản và KB matcher]] | normalize A4/B2, token bảo vệ, phát hiện không dấu, tách từ, SkillMatcher, tra chức danh/cấp bậc/ngành | `core/text`, `core/kb` | T00 (dùng KB mini, không chờ T01) | P1 | ✅ 15/11 |
| [[T03 Core - encoder bge-m3]] | nạp bge-m3 một lần: dense + sparse, token embedding layer 24; FakeEncoder | `core/models` | T00 | P1 | ✅ 16/11 |
| [[T04 Ingest CV - A1 đến A9]] | CV JSON → `cv_record` đầy đủ trừ vector (không DB, không GPU) | `ingest/cv` | T02 | P1 | ✅ 15/11 |
| [[T05 Ingest CV - A10, A11 và CLI]] | embedding, ghi một giao dịch, `ingest_log`, `unknown_skill`, CLI | `ingest/cv` | T03, T04 | P1 | ✅ 15/11 (thiếu reprocess) |
| [[T06 Ingest JD - Luồng B]] | B1–B8 trọn vẹn | `ingest/jd` | T02, T03, T05 (dùng lại writer) | P1 | ✅ 15/11 |
| [[T07 Script độ phủ Module 1]] | đếm tỉ lệ có từng trường trên CV/JD thật → báo cáo bật/tắt feature | `evaluation` | T04 (dùng schema) | P0 | ☐ |
| [[T08 Retrieve - chỉ mục trong RAM]] | dựng ma trận vector, gạch, CV × kỹ năng, BM25 từ Postgres; cập nhật tăng dần | `retrieve` | T05, T06 | P1 | ✅ 16/11 |
| [[T09 Retrieve - Luồng C]] | C1–C8: 4 góc nhìn, min–max, hợp nhất, top K, giải thích sơ bộ, log, RerankRequest | `retrieve` | T08 | P1 | ✅ 16/11 |
| [[T10 Rerank - BERTScore engine và golden test]] | chuẩn bị đầu vào, cache token, R_ij + căn khớp token, golden G1 | `rerank/bertscore`, `evaluation` | T02, T03 | P1 | ✅ 16/11 |
| [[T11 Rerank - feature P1 và chốt điểm]] | A1 (= s_skill), B4, B1, B2, thiếu dữ liệu, cổng, điểm 0–100, bảng rerank, FinalItem | `rerank` | T09, T10 | P1 | ✅ 16/11 |
| [[T12 Explain - mẫu xác định]] | EX1–EX4 dạng template, lười + cache | `explain` | T11 | P1 | ✅ 16/11 |
| [[T13 API và chạy trọn một JD]] | FastAPI cho backend Java; lệnh end-to-end JSON → giải thích | `api` | T12 | P1 (mốc xong P1) | ☐ |
| [[T14 Đánh giá - metric, nhãn, ablation]] | Recall@K, nDCG@10, bootstrap, runner ablation theo config, test bất biến, G2 | `evaluation` | T13 | P2 | ☐ |
| [[T15 Rerank - feature P2]] | A1/A2 qua `rel`, B5, B3, C1, view trách nhiệm hiệu chuẩn `lo/hi` | `rerank`, `retrieve` | T11, T01 (KB có quan hệ) | P2 | ☐ |
| [[T16 Luồng D - CV sang JD]] | chỉ mục phía JD, D1–D8, rerank chiều ngược, giải thích cho ứng viên | `retrieve`, `rerank`, `explain` | T15 | P3 | ☐ |
| [[T17 Backlog]] | Explain LLM, RR5, mốc R-X*, LoRA (file 12), HyDE, phục hồi dấu | nhiều | — | P2–P4 | ☐ |

**Mốc kiểm tra:**

- Sau **T06**: nạp được CV và JD mẫu, kiểm tay đủ 17 bảng.
- Sau **T13**: xong P1 của thiết kế — "chạy trọn một JD từ JSON đến giải thích; log đủ; so với R-A0".
- T01, T07 có thể chạy song song với T02–T06 (khác người/agent).

---

## 4. Việc cần người dùng chốt trước (chặn hoặc ảnh hưởng nhiều phần)

| # | Câu hỏi | Ảnh hưởng | Mặc định nếu chưa chốt |
| --- | --- | --- | --- |
| Q-1 | Schema thật của CV JSON và JD JSON (Module 1). Cần 3–5 file mẫu thật. | T04, T06, T07 | dùng schema giả định ở thiết kế 04, 05; cô lập trong lớp `adapter` để đổi tên trường dễ |
| Q-2 | Nhóm vai trò: thiết kế ghi **8**, KB hiện có **9** (đã tách AI/ML). | T01, T02, B1/B2 | theo KB (9 nhóm), sửa thiết kế 00 mục 3.3 |
| Q-3 | KB hiện toàn bộ là `candidate`. Có cho xuất `candidate` để dev trước khi duyệt không? | T01 | **ĐÃ CHỐT (14/11/2026): tạm thời xuất hết cả `candidate`.** Snapshot có hậu tố `-dev` và cột `status` cho từng kỹ năng |
| Q-4 | Công cụ tách từ tiếng Việt (pyvi / underthesea / VnCoreNLP). | T02 | `pyvi` sau một interface `Segmenter`, đổi được |
| Q-5 | Khoá bí mật HMAC cho `candidate_key`, cách lưu (env). | T05 | biến môi trường `CVMATCH_HMAC_KEY` |
| Q-6 | GPU chạy dịch vụ: GTX 1650 4 GB như lúc test? | T03, T10 | fp32, batch nhỏ, có tuỳ chọn CPU cho test |
| Q-7 | Backend Java gọi AI thế nào: HTTP (FastAPI) hay đọc chung DB? | T13 | HTTP FastAPI, AI có DB riêng (schema `match`) |
| Q-8 | Có bộ CV/JD thật (đã ẩn danh) để chạy T07 và gán nhãn T14 không, khi nào? | T07, T14 | dùng dữ liệu tổng hợp để chạy thử, đánh dấu rõ |
