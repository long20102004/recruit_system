# T08 · Retrieve: cấu trúc dữ liệu trong RAM

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `03` mục "Cấu trúc trong bộ nhớ" · `06` mục 2, 7 · `04` A9 (chỉ mục BM25), A11 (cập nhật sau commit).

## Mục tiêu

Dựng từ Postgres (nguồn sự thật) các cấu trúc mà 4 góc nhìn cần, chỉ gồm CV `status = active` và `is_latest = true`, cùng bộ phiên bản.

## Làm

`retrieve/index.py` — lớp `CvIndex`:

| Cấu trúc | Nội dung |
| --- | --- |
| `cv_ids: np.ndarray` | thứ tự hàng ↔ `cv_id` (+ dict ngược) |
| `doc_matrix` | n_cv × 1024, float16, đã chuẩn hoá L2 |
| `bullet_matrix` + `bullet_cv_index` + `bullet_ids` | n_bullet × 1024 float16; gạch i thuộc hàng CV nào; `bullet_id` tương ứng |
| `skill_matrix` | `scipy.sparse.csr` n_cv × n_skill, ô = `ev`; dict `skill_id → cột` |
| `bm25` | chỉ mục `bm25s` trên `bm25_noacc` (+ tuỳ chọn ghép `skill_tokens`, theo config); lưu `built_at` và IDF |
| `active_mask` | bool n_cv, để xoá/thay bản cũ **ngay** mà không dựng lại ma trận |

- `CvIndex.build(db, versions)`: đọc theo lô (không nạp hết một lần vào Python list), chỉ CV cùng `ontology_version`, `pipeline_version`, `embed_model` của config.
- `add(cv_id)` / `deactivate(cv_id)`: nghe sự kiện `CvCommitted` của T05 — thêm hàng (append, ma trận tăng theo khối), tắt bản cũ. CV mới **chưa** vào BM25 cho tới lần dựng lại; ghi rõ BM25 dùng IDF của lần dựng trước (thiết kế A9) — với CV mới, tính điểm BM25 bằng IDF cũ.
- `rebuild_bm25()`: theo lịch (lệnh `cvmatch retrieve rebuild-bm25`); có thể lưu ra file kèm ngày dựng để khởi động nhanh.
- `save/load` snapshot ra đĩa (tuỳ chọn) + lệnh `cvmatch retrieve rebuild` ("dựng lại từ Postgres").
- Kiểm nhất quán: `verify(db)` so số CV active, số gạch, checksum `cv_id` với Postgres.

## Không làm

Chấm điểm (T09), cấu trúc phía JD cho Luồng D (T16).

## Tiêu chí xong

- Build trên DB có 1.000 CV tổng hợp: đúng số hàng; `bullet_cv_index` đúng.
- `add` rồi `deactivate` bản cũ → CV cũ không còn được chấm, CV mới có mặt ở 3 view (dense, skill, resp).
- `verify` phát hiện lệch khi xoá tay một CV trong DB.
- Báo bộ nhớ RAM và thời gian build cho 1.000 / 10.000 CV tổng hợp; ngoại suy 100.000 so với ước lượng thiết kế (≈200 MB doc, ≈6 GB gạch).

## Ghi chú bàn giao

**Trạng thái: xong (16/11/2026).** `retrieve/index.py` (`CvIndex`), `retrieve/bm25.py` (`Bm25Index`); 4 test đơn vị BM25 + 4 test tích hợp.

- **Dùng:** `CvIndex(cfg).build(conn)`; `add(conn, cv_ids, replaced)`, `deactivate(cv_id)`, `attach_events(conn_factory)` (nghe `cv_committed`, `cv_deleted` ở **`core/events.py`** — đã chuyển từ `ingest` sang `core` để `retrieve` không import `ingest`); `rebuild_bm25(conn)`; `verify(conn)`; CLI `cvmatch retrieve verify`.
- **BM25 tự cài** (ma trận thưa, trọng số từng ô tính sẵn): đúng yêu cầu A9 "CV mới nạp trong ngày chấm bằng IDF của lần dựng trước" — `append` dùng IDF/avgdl cũ, từ mới bị bỏ qua tới lần `build` sau. Công thức idf dạng Lucene `ln(1 + (N − df + 0.5)/(df + 0.5))`. Không dùng `bm25s`.
- Gạch sắp theo hàng CV (để `np.maximum.reduceat`); bộ đệm float16 tăng gấp đôi khi nối thêm; `active` tắt CV cũ/xoá ngay.
- Chỉ nạp CV **cùng bộ phiên bản** (ontology, pipeline, embed_model) với config.
- **Số đo** (10.000 CV × 30 gạch tổng hợp): dựng 20,1 s; RAM doc 19,5 MB, gạch 586 MB, kỹ năng 0,9 MB, BM25 5,3 MB. Ngoại suy 100.000 CV: doc ≈ 195 MB, gạch ≈ 5,9 GB (khớp ước lượng thiết kế ≈ 200 MB / 6 GB), dựng ≈ 3–4 phút.
- **Lỗi lớn phát hiện nhờ T08 (đã sửa ở `core/db.py`):** `connect()` trước đây không autocommit → `SELECT` kiểm trùng (A2) ngầm mở giao dịch, `conn.transaction()` của A11 chỉ thành SAVEPOINT → dữ liệu chưa commit khi phát `cv_committed`. Nay `connect()` mặc định `autocommit=True`; có test hồi quy (kết nối khác phải thấy CV ngay lúc sự kiện phát).
- **Chưa làm:** lưu chỉ mục ra đĩa để khởi động nhanh (tuỳ chọn trong kế hoạch).
