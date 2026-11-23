# cvmatch — module match CV ↔ JD

Thiết kế: `services/cvmatch-ai/docs/Thiết kế/` (00–12). Kế hoạch và trạng thái từng phần: `services/cvmatch-ai/docs/Kế hoạch code/` (đọc `00 Tổng quan kế hoạch.md` trước).
Những chỗ còn chạy chưa đúng / cần tối ưu: [`docs/Vấn đề tồn tại và cần tối ưu.md`](docs/Vấn%20đề%20tồn%20tại%20và%20cần%20tối%20ưu.md).

Cấu hình đang bật (`config/active.yaml`): `prep-1.1` · `retrieve-1.0` · `rr-1.0` (P1: A1, B4, B1, B2) · `explain-1.1`.
`rr-1.1.yaml` bật đủ 8 feature (P2) — chỉ chuyển sang khi ablation trên nhãn thật cho thấy có ích.

## Cài đặt

```bash
# conda env riêng của module (clone từ module2, Python 3.11; GPU: torch + transformers đã có trong env)
conda activate cvmatch
pip install -e ".[dev]"

# PostgreSQL 16 + pgvector (cổng 5433). Sau khi khởi động lại máy: docker start cvmatch-postgres
docker compose up -d
python -m cvmatch.cli db migrate
python -m cvmatch.cli db status
```

Biến môi trường: xem `.env.example` (`CVMATCH_DB_URL`, `CVMATCH_HMAC_KEY`, `CVMATCH_DEVICE`, `CVMATCH_FAKE_ENCODER`). In tiếng Việt ra terminal Windows cần `PYTHONIOENCODING=utf-8`.

## Nạp KB snapshot

Snapshot xuất từ `tools/build_kb` (thư mục `build_kb/out/snapshot/<version>`):

```bash
python -m cvmatch.cli kb import ../../tools/build_kb/out/snapshot/kb-2026-11-24
python -m cvmatch.cli kb list
# rồi đặt `ontology_version: <version>` trong config/active.yaml
```

Chạy thử không cần KB thật: `--kb-dir tests/fixtures/kb_mini`.

## Chạy trọn một JD (mốc P1)

```bash
# FakeEncoder (không GPU), database mới riêng cho lần chạy
python -m cvmatch.cli run-e2e --cv-dir tests/fixtures/e2e/cv --jd tests/fixtures/e2e/jd \
    --kb-dir tests/fixtures/kb_mini --fake-encoder --fresh-db
# bge-m3 thật trên GPU
python -m cvmatch.cli run-e2e --cv-dir tests/fixtures/e2e/cv --jd tests/fixtures/e2e/jd \
    --kb-dir ../../tools/build_kb/out/snapshot/kb-2026-11-24 --fresh-db
```

migrate → nạp KB (nếu chưa có) → nạp CV, JD → Retrieve → Rerank → Explain top 5. Kết quả ở `reports/e2e/<thời điểm>/`:
`report.md` (top sau rerank, **top 30 theo `fused` của Retrieve để so với R-A0**, giải thích), `summary.json`, log JSON `run.jsonl` (`run_id` xuyên suốt, thời gian từng tầng).
Bộ fixture (34 CV tổng hợp, 3 JD) sinh lại bằng `python tests/fixtures/e2e/make_fixtures.py`.

## Môi trường demo: thử API như thật (DB thật, vài trăm CV đã nạp)

```bash
python -m cvmatch.cli demo seed            # ~3 phút trên GPU: sinh 300 CV + 10 bản CV mới + 30 JD (dữ liệu giả),
                                           # tạo DB `cvmatch_demo`, migrate, nạp KB kb-2026-11-21-4, nạp qua Luồng A/B
python -m cvmatch.cli demo serve           # API trên DB demo: http://127.0.0.1:8090/docs
python -m cvmatch.cli demo scenarios       # cửa sổ khác: 14 kịch bản HTTP -> reports/demo/scenarios.md
python -m pytest -m live                   # cùng các kịch bản dưới dạng pytest (server phải đang chạy)
```

- Dữ liệu ở `data/demo/` (không commit): `cv/`, `cv_updates/` (cùng email, bản mới hơn → version 2), `jd/` (27 open,
  2 closed, 1 draft), `manifest.json` (vai trò / nhóm / cấp bậc thật của từng file), `state.json` (DB, KB, file → `cv_id`).
- Dữ liệu đa dạng có chủ đích: 23 vai trò, 6 cấp bậc, mô tả dạng mảng / đoạn văn / tiếng Anh / trống, 9 định dạng ngày,
  tên trường kiểu khác (adapter), CV không dấu, câu phủ định, mô tả học tập, sinh viên, đổi nghề.
- `--fake-encoder` (không GPU), `--n-cv 500 --regenerate` (đổi kích thước), `--reset` (xoá DB demo, nạp lại).
- Kịch bản thay đổi dữ liệu dùng CV/JD riêng của lần chạy và dọn dẹp ở cuối; **không chạy hai lần `scenarios` cùng lúc**
  (một lần đóng/mở JD sẽ làm lần kia sai số đếm).
- Gọi tay: mở `/docs`, hoặc lấy `cv_id` / `jd_id` trong `data/demo/state.json`.
- Đối chiếu kết quả với dữ liệu gốc: `python -m cvmatch.cli demo inspect <run_id>` (top N kèm file JSON gốc, nhóm /
  cấp / số năm thật, kỹ năng, điểm từng feature, CV đúng nhóm bị xếp ngoài top N) và
  `python -m cvmatch.cli demo show <cv_id | DEMO-xxx | tên file>` (JSON gốc của một CV / JD).
- Postman: `python -m cvmatch.cli demo postman` → import `data/demo/postman/cvmatch_demo.postman_collection.json` và
  `…postman_environment.json`, chọn environment "cvmatch demo", chạy thư mục 0 → 6 (thư mục 6 dọn dữ liệu vừa tạo).
  Collection có thể import thẳng từ OpenAPI: `http://127.0.0.1:8090/openapi.json`.

## API cho backend Java

```bash
python -m cvmatch.cli api serve --port 8090 [--fake-encoder]     # hoặc: uvicorn cvmatch.api.app:app
```

Khởi động nạp config, KB snapshot (`active.yaml`), encoder, chỉ mục CV trong RAM **một lần**. OpenAPI: `GET /openapi.json`, thử tay: `/docs`.

| Phương thức | Đường dẫn | Việc |
| --- | --- | --- |
| `POST` | `/cv` | Luồng A cho 1 CV → `{cv_id, status, flags}` (`invalid` → 422) |
| `POST` | `/cv/batch` | nạp theo lô, mặc định chạy nền → `202 {job_id}` |
| `DELETE` | `/cv/{cv_id}` | xoá theo yêu cầu (gỡ khỏi RAM, xoá cache BERTScore); xoá lần 2 → 404 |
| `POST` | `/jd` | Luồng B → `{jd_id, version, status, warnings}` |
| `PATCH` | `/jd/{jd_id}/status` | `open / draft / closed / expired` |
| `POST` | `/match/jd/{jd_id}` | `{K, N, hard_filters, exclude_cv_ids, include_cv_ids, views, ref_ym, background}` → top N `{cv_id, rank, score, band, cap_applied, flags, features, skills}` + `run_id` |
| `GET` | `/match/{run_id}/cv/{cv_id}/explain` | giải thích cho HR (lười, có cache) |
| `POST` | `/match/cv/{cv_id}` | Luồng D: CV → top N JD đang mở (`{K, N, hard_filters, exclude_jd_ids, include_jd_ids, …}`) |
| `POST` | `/match/cv:preview` | CV tạm của ứng viên → JD gợi ý + giải thích; **không lưu lại gì** |
| `GET` | `/match/{run_id}/jd/{jd_id}/explain` | giải thích hướng ứng viên (không hiện điểm số) |
| `GET` | `/jobs/{job_id}` | trạng thái việc chạy nền |
| `GET` | `/health` | bộ khoá phiên bản, `config_hash`, số CV trong chỉ mục, `db`; DB lỗi → 503 |

- `include_cv_ids` / `include_jd_ids`: chỉ xét các CV / JD này (ứng viên đã nộp đơn, chấm một cặp); id không có → cảnh báo
  `include_unknown`. Điểm phụ thuộc pool (chuẩn hoá min–max, `pool_median`): cùng cặp trong pool nhỏ có thể khác điểm
  trong pool lớn.
- Mỗi dòng kết quả có `features` (A1…C1 trong [0, 1], `null` = tắt hoặc thiếu dữ liệu) và `skills {met, partial, missing}`
  (tên hiển thị của KB), để backend không phải gọi explain cho từng dòng.
- Hợp đồng cho phía Java: `openapi.json` (sinh lại sau khi đổi `api/schemas.py`, xem mục "Chạy như service").

## Chạy như service (Docker, HireLens)

```bash
docker build -t cvmatch-ai services/cvmatch-ai                                    # CPU (torch CPU, image ~2 GB)
docker build -t cvmatch-ai --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cu130 services/cvmatch-ai   # GPU
```

Lệnh của container: `cvmatch api prod` → chờ Postgres → `db migrate` → nếu `ontology_version` chưa có thì `kb import
$CVMATCH_KB_DIR/<version>` → API trên `0.0.0.0:$CVMATCH_PORT` (1 worker). Khởi động lại không làm gì thêm.

| Biến | Ý nghĩa |
| --- | --- |
| `CVMATCH_ENV=prod` | mặc định trong image: bắt buộc `CVMATCH_SERVICE_TOKEN`, `CVMATCH_HMAC_KEY` thật (không `change-me`) |
| `CVMATCH_SERVICE_TOKEN` | mọi request trừ `/health` (kể cả `/docs`, `/openapi.json`) phải có header `X-Service-Token`; sai → 401 |
| `CVMATCH_DB_URL`, `CVMATCH_HMAC_KEY` | như khi chạy tay. Đổi khoá HMAC = mọi `candidate_key` đổi → phải nạp lại CV |
| `CVMATCH_KB_DIR` (`/kb`) | mount `tools/build_kb/out/snapshot` read-only |
| `CVMATCH_ONTOLOGY_VERSION` | ghi đè `active.yaml` (vào bộ khoá phiên bản) |
| `CVMATCH_DEVICE` (`cpu`) | `cuda` với image GPU |
| `HF_HOME` | gắn volume: bge-m3 (~2,3 GB) tải lần đầu, `start_period` của healthcheck là 600 s |

Thư viện của image ghim ở `docker/requirements.lock.txt` (cùng phiên bản env `cvmatch` đã chạy qua test).
Sinh lại hợp đồng API: `CVMATCH_SERVICE_TOKEN= python -c "import json; from cvmatch.api.app import create_app; print(json.dumps(create_app(lambda: None).openapi(), ensure_ascii=False, indent=2))" > openapi.json`.

## Đổi phiên bản (KB / chuẩn hoá / model)

```bash
python -m cvmatch.cli db versions                       # các bộ khoá trong kho, * = active.yaml
python -m cvmatch.cli reprocess cv --from A5            # KB mới: giữ vector · A8: đổi chuẩn hoá · A10: đổi model
python -m cvmatch.cli reprocess jd
```

Bản mới ghi **song song**, bản cũ vẫn match được bằng cấu hình cũ. Đánh giá bản mới (`eval ablation --kb-version …`) rồi sửa `config/active.yaml` để chuyển cùng lúc CV + JD.
`prep-1.1` (đang bật) thêm câu `summary` cho B5: kho nạp bằng `prep-1.0` chạy `reprocess cv --from A8` + `reprocess jd`.

## Đánh giá (T14)

```bash
python -m cvmatch.cli eval pool --out reports/labels/to_label.csv     # gộp top-300 RT-*, top-60 R-*, 20 ngẫu nhiên
python -m cvmatch.cli eval kappa graded.csv                            # đồng thuận 2 người chấm
python -m cvmatch.cli eval split --labels graded.csv                  # dev/test 50/50 phân tầng
python -m cvmatch.cli eval ablation experiments/rerank_R.yaml --labels graded.csv --split reports/labels/split.json
python -m cvmatch.cli eval calibrate pairs.csv                         # lo/hi + ngưỡng mức khớp (in, không sửa)
python -m cvmatch.cli eval invariance --cv-dir <dir> --jd <dir> --kb-dir <snapshot>   # DB riêng
python -m cvmatch.cli eval g2 --kb-dir <snapshot>                      # golden qua cả pipeline (DB riêng)
python -m cvmatch.cli eval prep-sample / prep-score                    # kiểm tay tiền xử lý
python -m cvmatch.cli eval fp16                                        # lệch fp16 vs fp32 trên golden
```

Kế hoạch thí nghiệm (phần ghi đè config) ở `experiments/`: `retrieve_RT.yaml`, `rerank_R.yaml`, `reverse_RT_R.yaml`. Định dạng nhãn: `src/cvmatch/evaluation/labels/__init__.py`.

## Lệnh khác

```bash
python -m cvmatch.cli config show                                   # bộ khoá phiên bản + config_hash
python -m cvmatch.cli ingest cv <file|thư mục> [--kb-dir <snapshot>] [--fake-encoder]
python -m cvmatch.cli ingest jd <file|thư mục> [--kb-dir <snapshot>] [--fake-encoder]
python -m cvmatch.cli jd status <jd_id> closed
python -m cvmatch.cli delete cv <cv_id>
python -m cvmatch.cli retrieve jd <jd_id>                           # Luồng C, in top K
python -m cvmatch.cli retrieve cv <cv_id>                           # Luồng D, in top K JD
python -m cvmatch.cli rerank <retrieve_run_id>                      # Tầng 2 (cả hai chiều)
python -m cvmatch.cli explain <rerank_run_id> <cv_id | jd_id>       # Tầng 3 (HR / ứng viên theo chiều)
python -m cvmatch.cli eval golden [--bare] [--bench]                # golden BERTScore (G1)
python -m cvmatch.cli eval coverage --cv <dir> --jd <dir> --out reports/coverage.md   # độ phủ Module 1 (T07)
```

## Test

```bash
python -m pytest -q          # đơn vị + tích hợp DB (tự skip nếu không có Postgres)
python -m pytest -m gpu      # cần bge-m3 thật (tải ~2,3 GB lần đầu)
```

## Cấu trúc

`core` (config, db, contracts, text, kb, models) ← `ingest` (Luồng A, B) · `retrieve` · `rerank` ← `explain` · `api`, `evaluation`.
Các package chỉ trao đổi qua Postgres và `core/contracts.py`, không import chéo.

**Lưu ý hiệu năng:** không dùng `cursor.executemany` khi ghi (pipeline mode của psycopg 3 bị trễ ~40 ms mỗi lần gọi trên Windows/Docker Desktop). Dùng `ingest.common.writer.insert_rows`.
