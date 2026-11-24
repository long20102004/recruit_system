# ai-service

Toàn bộ phần AI của HireLens, chia theo 3 module nghiệp vụ. Mỗi thư mục con là một project độc lập: có dependency, test và Dockerfile riêng. Chạy lệnh bên trong thư mục của module đó.

| Module | Thư mục | Người phụ trách | Service compose | Cổng host | Profile |
|---|---|---|---|---|---|
| M1 · Trích xuất CV | `extraction/` | Hocnv | `cv-extraction-ai` | 8001 | `cv-ai` |
| M2 · Matching CV ↔ JD | `matching/service/` | nguyenloc | `cvmatch-ai` (+ `cvmatch-db`) | 8003 | `match` |
| M2 · Knowledge Base kỹ năng | `matching/kb-builder/` | nguyenloc | (không chạy service; xuất snapshot mount vào `cvmatch-ai`) | – | – |
| M3 · Chấm phỏng vấn | `interview/service/` | longhh | `interview-ai` | 8000 | `ai` |
| M3 · Mẫu barem | `interview/rubric-templates/` | longhh | – | – | – |
| Trọng số dùng chung | `models/` | – | mount `models/cv-extraction` vào `cv-extraction-ai` | – | – |

Tên service, cổng, biến môi trường (`AI_URL`, `CV_EXTRACTION_URL`, `CVMATCH_URL`) và API không đổi so với trước khi gom thư mục.

## Chạy

Từ thư mục gốc repo:

```bash
# Đặt ai-service/models/cv-extraction/model-v4-q4_k_m.gguf trước khi bật cv-ai
docker compose --profile ai --profile cv-ai --profile match up -d --build
```

## Test từng module

| Module | Lệnh (chạy trong thư mục module) |
|---|---|
| `extraction/` | `python -m pytest -q` (xem `extraction/README.md`) |
| `matching/service/` | Xem `matching/service/README.md`; test tích hợp cần Postgres |
| `matching/kb-builder/` | `python -m pytest tests` |
| `interview/service/` | Xem `interview/service/README.md` |

## Đường dẫn cũ → mới

| Trước | Sau |
|---|---|
| `ai-service/` (M1 nghiên cứu) và `services/cv-extraction-ai/` | `extraction/` (đã gộp, bỏ bản trùng) |
| `services/cvmatch-ai/` | `matching/service/` |
| `tools/build_kb/` | `matching/kb-builder/` |
| `AI/` | `interview/service/` |
| `templates/barem/` | `interview/rubric-templates/` |
| `models/` | `models/` |

Thư mục của M2 và M3 chỉ được di chuyển, nội dung không đổi. Một số tài liệu và script phụ bên trong các module này vẫn nhắc đường dẫn cũ. Owner của module sẽ tự cập nhật.
