# cvmatch — module match CV ↔ JD

Thiết kế: `ai/docs/Thiết kế/` (00–12). Kế hoạch và trạng thái từng phần: `ai/docs/Kế hoạch code/` (đọc `00 Tổng quan kế hoạch.md` trước).

## Cài đặt

```bash
# conda env riêng của module (clone từ module2, Python 3.11)
conda activate cvmatch
pip install -e ".[dev]"

# PostgreSQL 16 + pgvector (cổng 5433)
docker compose up -d
python -m cvmatch.cli db migrate
python -m cvmatch.cli db status
```

Biến môi trường: xem `.env.example` (`CVMATCH_DB_URL`, `CVMATCH_HMAC_KEY`, `CVMATCH_DEVICE`, `CVMATCH_FAKE_ENCODER`).

## Lệnh

```bash
python -m cvmatch.cli config show                                   # bộ khoá phiên bản + config_hash
python -m cvmatch.cli ingest cv <file|thư mục> --kb-dir <snapshot> [--fake-encoder]
python -m cvmatch.cli ingest jd <file|thư mục> --kb-dir <snapshot> [--fake-encoder]
python -m cvmatch.cli jd status <jd_id> closed
python -m cvmatch.cli delete cv <cv_id>
```

Chưa có snapshot KB thật (T01) thì dùng `--kb-dir tests/fixtures/kb_mini`.

## Test

```bash
python -m pytest -q          # đơn vị + tích hợp DB (tự skip nếu không có Postgres)
python -m pytest -m gpu      # cần bge-m3 thật (tải ~2,3 GB lần đầu)
```

## Cấu trúc

`core` (config, db, contracts, text, kb, models) ← `ingest` (Luồng A, B) · `retrieve` · `rerank` ← `explain` · `api`, `evaluation`.
Các package chỉ trao đổi qua Postgres và `core/contracts.py`, không import chéo.

**Lưu ý hiệu năng:** không dùng `cursor.executemany` khi ghi (pipeline mode của psycopg 3 bị trễ ~40 ms mỗi lần gọi trên Windows/Docker Desktop). Dùng `ingest.common.writer.insert_rows`.
