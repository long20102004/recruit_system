# T13 · API cho backend và chạy trọn một JD (mốc hoàn thành P1)

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `00` mục 1 · `06` mục 4.1 · `07` mục 6 · `08` mục 2 · `11` lộ trình P1. Xem nhanh `backend/` (Spring Boot) chỉ để biết cách gọi, **không sửa** backend.

## Mục tiêu

1. Một lệnh chạy **trọn** JD từ JSON → giải thích, log đủ.
2. Dịch vụ HTTP để backend Java gọi (Q-7).

## Làm

1. `api/app.py` (FastAPI), khởi động: nạp config, KB snapshot, encoder, `CvIndex` (T08) **một lần**; đăng ký listener `CvCommitted` → `CvIndex.add`.
   - `POST /cv` (body CV JSON) → chạy Luồng A → `{cv_id, status, flags}`; `DELETE /cv/{cv_id}`.
   - `POST /jd`, `PATCH /jd/{jd_id}/status`.
   - `POST /match/jd/{jd_id}` (`K`, `N`, lọc cứng, `exclude_cv_ids`) → Retrieve + Rerank → top N `{cv_id, rank, score, band, cap_applied, flags}` + `run_id`.
   - `GET /match/{run_id}/cv/{cv_id}/explain` → Explain lười.
   - `GET /health` (phiên bản: ontology, pipeline, embed_model, bertscore_config, rr config).
   - Request/response bằng pydantic, sinh OpenAPI cho phía Java.
   - Nạp CV theo lô và rerank lâu → endpoint chạy nền + `GET /jobs/{id}` (đơn giản, trong tiến trình).
2. `cvmatch run-e2e --cv-dir <dir> --jd <file>`: migrate (nếu cần) → import KB → nạp CV, JD → retrieve → rerank → explain top 5 → in kết quả + đường dẫn log.
3. **So với R-A0**: cùng lần chạy, xuất cả top 30 theo `fused` của Retrieve (không rerank) để so sánh tay.
4. Log có cấu trúc (JSON) với `run_id` xuyên suốt; thời gian từng tầng.
5. README trong `ai/cvmatch/`: cài đặt, chạy docker, migrate, import KB, chạy API, chạy test (thường / gpu).

## Tiêu chí xong

- `run-e2e` chạy được trên bộ fixture (≥ 30 CV tổng hợp đa vai trò + 3 JD) với FakeEncoder, và trên GPU với bge-m3 thật.
- Test API bằng `TestClient`: luồng nạp → match → explain trả mã 200, đúng schema.
- Mọi bản ghi `match_run`, `rerank_run` có đủ khoá phiên bản và `config_json`.
- Đây là mốc P1 của thiết kế: ghi vào bàn giao các số đo (thời gian mỗi tầng, bộ nhớ) và danh sách giả định còn treo.

## Ghi chú bàn giao

_(agent điền)_
