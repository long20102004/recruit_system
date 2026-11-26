# T05 · Ingest CV: A10 embedding, A11 ghi một giao dịch, CLI

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `04` A10, A11 · `03` mục "`cv_record` là gì", "Khi có thay đổi", "Lỗi thường gặp", "Quyền riêng tư".

## Mục tiêu

Biến `CvRecord` của T04 thành dữ liệu trong Postgres, **hoặc đủ hết, hoặc không có gì**.

## Làm

1. `ingest/cv/embed.py`: dense + sparse của `doc_text` (bản A8 đã viết thường nhưng **còn dấu**, đúng ý "văn bản tài liệu có dấu" của A10; không dùng bản không dấu của A9); dense của từng `context_text`. Theo lô nhiều CV một lần. Lưu float16.
2. `ingest/common/writer.py` (dùng chung với JD ở T06): helper ghi nhiều bảng trong một `transaction()`, thử lại tối đa 3 lần khi lỗi tạm thời, rồi `status = failed` + `ingest_log`.
3. `ingest/cv/write.py`: đúng **thứ tự 8 bước** ở thiết kế A11:
   - `cv` (bản cũ cùng `candidate_key` → `is_latest = false`), `cv_meta` (gồm `n_bullets`), `cv_experience`, `cv_education`, `cv_skill`, `cv_bullet` → lấy `bullet_id` → `cv_bullet_vector` → điền `cv_skill.bullet_id`, `cv_vector`, `cv_bm25_doc`, `unknown_skill` (upsert tăng `count`), `ingest_log` `ok`.
   - Ghi 3 cột phiên bản.
   - Dừng sớm (invalid, duplicate) → chỉ ghi `ingest_log` ngay.
4. `ingest/cv/dedup_pg.py`: cài `DedupLookup` của T04 trên Postgres.
5. **Sự kiện sau commit**: phát `CvCommitted(cv_id, replaced_cv_id)` qua một hook đơn giản (danh sách callback / bảng `outbox`) để T08 cập nhật RAM. Ở phần này chỉ cần phát, chưa có người nghe.
6. `ingest/cli.py`:
   - `cvmatch ingest cv <file|thư mục> [--batch 32]`
   - `cvmatch reprocess cv --from A5|A8|A10` (chạy lại từ bước đó cho toàn kho, theo bảng "Khi có thay đổi" của thiết kế 03; ghi phiên bản mới song song, chưa cần quy trình chuyển phiên bản đầy đủ).
   - `cvmatch delete cv <cv_id>`: `status = deleted`, xoá `raw_json`, vector, `evidence_snippet`, gạch; xoá cache BERTScore theo `text_hash` gạch (gọi hàm rỗng nếu T10 chưa có, để TODO).

## Không làm

Cập nhật cấu trúc RAM của Retrieve (T08).

## Tiêu chí xong

- Integration test (DB thật trong docker, `FakeEncoder`): nạp CV mẫu → đủ dòng ở 9 bảng `cv*`, `bullet_id` liên kết đúng.
- Nạp lại đúng file đó → `duplicate`, không thêm dòng.
- Nạp bản mới cùng email → `version = 2`, bản cũ `is_latest = false`.
- Giả lập lỗi ở bước ghi vector → **không** bảng nào có dữ liệu của CV đó; `ingest_log` ghi lỗi.
- Xoá CV → không còn nội dung cá nhân ở các bảng chấm điểm.
- Báo tốc độ: số CV/phút khi nạp 1.000 CV tổng hợp (Fake và GPU nếu có).

## Ghi chú bàn giao

**Trạng thái: xong phần chính (15/11/2026), còn thiếu `reprocess`.** 12 test tích hợp trên Postgres thật (`tests/integration/test_ingest_cv_db.py`), toàn bộ 94 test qua.

- **Dùng:** `CvIngestor(conn, ctx, encoder).ingest_many([(nguồn, json), ...]) -> [IngestOutcome]`; `delete_cv(conn, cv_id)`. CLI: `cvmatch ingest cv <file|thư mục> --kb-dir <snapshot> [--fake-encoder] [--batch 32]`, `cvmatch delete cv <cv_id>`.
- **Sự kiện** (`ingest/common/events.py`): `cv_committed(CvCommitted)` phát sau commit → T08 đăng ký để thêm vào RAM; `cv_deleted(CvDeleted(cv_id, bullet_texts_raw))` → T10 xoá cache BERTScore theo `text_hash`, T08 gỡ khỏi RAM. Có sẵn `jd_committed`, `jd_status_changed` cho T06.
- **Dùng chung cho T06** (`ingest/common/writer.py`): `insert_rows` (chèn nhiều dòng bằng MỘT lệnh), `with_retry`, `log_ingest(_now)`, `upsert_unknown_skills(cur, [(text, example, n)], source)`, `halfvec`, `jsonb`.
- **Quyết định / lệch thiết kế:**
  - **Ghi theo lô trong một giao dịch** (`write_cvs`), lô lỗi → rollback rồi ghi lại từng CV. Vẫn đúng "không có CV ghi dở". Lý do đo được: trên Docker Desktop/Windows mỗi lệnh mang dữ liệu > ~4 KB bị trễ cố định ~42 ms (tầng mạng), và `executemany` của psycopg 3 (pipeline mode) cũng bị. Tốc độ: 317 → **3.154 CV/phút** (1.000 CV × 30 gạch, FakeEncoder). **Không dùng `cursor.executemany` ở code ghi.** URL mặc định đổi sang `127.0.0.1` (qua `localhost` có lúc chậm bất thường).
  - `cv_bullet` chèn trước `cv_skill` để có ngay `bullet_id` (cùng giao dịch nên tương đương "điền sau").
  - `cv_experience.idx` đánh liền cho cả kinh nghiệm (mới → cũ) rồi dự án; phân biệt bằng `kind`.
  - Hai bản cùng người trong một lô: chỉ bản version cao nhất `is_latest`. Trùng nội dung trong cùng lô cũng bị bắt (`BatchDedup`).
  - Lỗi embedding/ghi sau 3 lần → `ingest_log.status = 'failed'`, **không tạo dòng `cv`** (thiết kế ghi "status = failed"; chọn không ghi gì cho đúng "không ghi gì cho CV đó").
  - Xoá CV: thêm xoá `title_raw`, `major_raw`; `unknown_skill.example` có thể chứa chữ của CV, chưa xoá theo CV (không liên kết được) — ghi nhận.
- ~~Chưa làm reprocess~~ → **xong 23/11/2026** (xem mục dưới).

**Bổ sung 23/11/2026 — `reprocess`** (`ingest/reprocess.py`, test `tests/integration/test_reprocess_db.py`):

- `cvmatch reprocess cv --from A5|A8|A10 [--batch 32] [--limit n]`, `cvmatch reprocess jd`, `cvmatch db versions` (liệt kê các bộ khoá phiên bản trong kho, `*` = bộ của `active.yaml`).
- Ghi **song song**: CV mới có `cv_id` mới, cùng `candidate_key` / `version` / `content_hash`, bộ khoá mới; bản cũ giữ nguyên, vẫn match được bằng cấu hình cũ. JD: Luồng B lại trên `raw_json` → version mới ở bộ khoá mới; Retrieve chọn bản JD mới nhất **cùng bộ khoá** (cả `jd_to_cvs.load_jd` lẫn `JdIndex`).
- Dùng lại vector chỉ khi **cùng `embed_model`**: `--from A5` giữ vector tài liệu + gạch (thiết kế: KB mới không cần tính lại); `--from A8` dùng lại khi văn bản đưa vào embed không đổi; `--from A10` (hoặc model khác) tính lại hết.
- Migration `008_parallel_versions.sql`: unique `(candidate_key, version)` → thêm 3 cột bộ khoá. `is_latest` của CV tính theo từng bộ khoá. A2 (`PgDedup`) chỉ coi là trùng / bản cũ trong **cùng** bộ khoá. Trạng thái tin tuyển dụng (`set_jd_status`) áp cho **mọi** bản của JD (không thì bản cũ còn `open` làm JD đã đóng hiện lại). Xoá CV xoá cả bản song song.
- Giả định: chạy lại từ `cv.raw_json` (đã qua adapter + sửa ngày) — idempotent, riêng cờ "ngày chỉ có năm" của lần nạp đầu không còn. Đã chạy thật trên DB dev (5 CV, 1 JD → `prep-1.1`, dùng lại toàn bộ vector).
