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
5. README trong `services/cvmatch-ai/`: cài đặt, chạy docker, migrate, import KB, chạy API, chạy test (thường / gpu).

## Tiêu chí xong

- `run-e2e` chạy được trên bộ fixture (≥ 30 CV tổng hợp đa vai trò + 3 JD) với FakeEncoder, và trên GPU với bge-m3 thật.
- Test API bằng `TestClient`: luồng nạp → match → explain trả mã 200, đúng schema.
- Mọi bản ghi `match_run`, `rerank_run` có đủ khoá phiên bản và `config_json`.
- Đây là mốc P1 của thiết kế: ghi vào bàn giao các số đo (thời gian mỗi tầng, bộ nhớ) và danh sách giả định còn treo.

## Ghi chú bàn giao

**Trạng thái: xong (23/11/2026) — mốc P1.** 190 test qua (`python -m pytest -q`), trong đó `tests/integration/test_api.py` (TestClient + run-e2e trên Postgres thật, FakeEncoder, KB mini).

- **Code:** `api/services.py` (`Services`: nạp config, KB, encoder, `CvIndex` một lần; khoá chung cho mọi thao tác dùng chỉ mục/encoder; nghe `cv_committed` → `CvIndex.add`, `cv_deleted` → gỡ RAM + xoá cache BERTScore; `config_and_encoder(fake=...)`), `api/app.py` (`create_app`, `app` cho uvicorn), `api/schemas.py` (pydantic → OpenAPI), `api/jobs.py` (việc chạy nền 1 luồng, trong tiến trình), `api/logjson.py` (log JSON, `run_id`), `api/e2e.py` + `api/cli.py`.
- **Lệnh:** `cvmatch api serve [--port 8090] [--fake-encoder]`; `cvmatch run-e2e --cv-dir <dir> --jd <file|dir> [--kb-dir <snapshot>] [--fake-encoder] [--fresh-db]`. Endpoint và cách chạy: README `services/cvmatch-ai/README.md`.
- **Fixture:** `tests/fixtures/e2e/` — 34 CV tổng hợp (9 vai trò, có biến thể: đoạn văn, không gạch, không dấu, ngày lạ, đổi nghề, dự án cá nhân) + 3 JD (Java có required/importance, FE, Data không có required). Sinh lại bằng `make_fixtures.py`.
- **R-A0:** `report.md` có bảng top 30 theo `fused` của Retrieve kèm hạng/điểm sau rerank.
- **Sửa ngoài `api` (nhỏ):** `rerank_run.config_json` thêm `versions` (đủ 5 khoá) và `bertscore` (cấu hình đầy đủ); `pyproject.toml` thêm `scipy` (đã dùng nhưng thiếu), `fastapi`, `uvicorn`, dev: `httpx`, `psutil`.
- **Lỗi đã gặp và xử lý:** dịch vụ khởi động với kho rỗng → BM25 có từ vựng rỗng, CV thêm tăng dần (T08 `append`) đều được điểm bm25 = 0. `Services` dựng lại BM25 sau lô nạp khi kho tăng > 10% so với lần dựng trước (`bm25_rebuild_growth`). Có test chặn.

**Số đo (GTX 1650, bge-m3 thật, KB `kb-2026-11-21-4`, 34 CV / 3 JD; chạy lại 23/11 với `prep-1.1`, `reports/e2e/20261123-152218/`, DB `cvmatch_e2e_20261123_152218`):**

| Mục | Giá trị |
| --- | --- |
| nạp encoder | 16,6–20,2 s (một lần lúc khởi động) |
| nạp 34 CV (A1–A11) | 5,9–7,0 s (~0,2 s/CV) · 3 JD 0,4–0,7 s |
| Retrieve / JD | 0,03–0,04 s |
| Rerank / JD (34 CV) | 0,59–0,64 s JD đầu (cache token lạnh), 0,11–0,14 s các JD sau |
| Explain top 5 | 0,18–0,20 s |
| RAM tiến trình / GPU đỉnh | 1,47 GB / 2,30 GB |
| chỉ mục RAM | < 0,4 MB (34 CV) |

Thứ hạng hợp lý khi so tay: JD Java → 7 CV java đứng đầu; JD FE → 5 frontend rồi 3 fullstack; JD Data → 4 CV data. Rerank đổi vài vị trí trong nhóm đầu so với `fused` (R-A0), đẩy CV khác vai trò xuống.

**Giả định còn treo:**
- Dữ liệu là tổng hợp; số đo trên 34 CV không đại diện cho 200 CV × 8 gạch (xem `eval golden --bench`). Cần CV/JD thật (Q-8).
- Việc chạy nền mất khi khởi động lại tiến trình; một luồng xử lý (khoá chung). Chưa có xác thực giữa backend Java và API (mặc định chỉ nghe `127.0.0.1`).
- BM25 tăng dần vẫn dùng IDF cũ giữa hai lần dựng; chưa có lịch dựng lại theo đêm.
- `/health` không kiểm DB/GPU sâu; `DELETE /cv` gọi lại trên CV đã xoá vẫn trả 200 (hàm `delete_cv` của T05 không lọc `status = deleted`).
- Cảnh báo "văn bản truy vấn < 50 từ" hiện với JD fixture ngắn — đúng như thiết kế.
- Tên kỹ năng trong KB thật có chỗ viết thường (vd `java`) → hiện nguyên trong giải thích; sửa ở phía KB (`build_kb`).
- Chưa làm `cvmatch reprocess` (T05) — vẫn để T17/quy trình chuyển phiên bản.

