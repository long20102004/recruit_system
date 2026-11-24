# Kế hoạch refactor: gom phần AI về `ai-service/`

Ngày lập: 24/11/2026. Căn cứ: nhánh `origin/develop` (đã merge PR #6 `locnh/cvmatch-update`) và nhánh `dev_hocnv`.

## 1. Hiện trạng

Code AI đang nằm ở 7 nơi, do 3 người phụ trách:

| Thư mục hiện tại | Nội dung | Module | Người phụ trách | Có trên `develop`? |
|---|---|---|---|---|
| `ai-service/` | Mã nghiên cứu M1: `app/` (bản cũ), `training/`, `eval/`, `kb/` (script build KB), notebook Colab, `tests/`; khoảng 12 GB file local (trọng số, data) không nằm trong Git | M1 – Trích xuất CV | Hocnv | Không, chỉ có trên `dev_hocnv` |
| `services/cv-extraction-ai/` | Bản serving M1 đang chạy trong compose (cổng 8001), copy từ `hocnv/DO-06` | M1 | Hocnv (longhh tích hợp) | Có |
| `models/cv-extraction/` | Chỗ đặt file `.gguf`, mount vào cv-extraction-ai | M1 | Hocnv | Có (chỉ `.gitignore`) |
| `services/cvmatch-ai/` | Service matching CV–JD (Postgres riêng, cổng 8000 nội bộ) | M2 – Matching | nguyenloc | Có |
| `tools/build_kb/` | Pipeline xây Knowledge Base, xuất snapshot mount vào cvmatch-ai | M2 | nguyenloc | Có |
| `AI/` | Service chấm phỏng vấn (BERTScore + rubric), data câu hỏi, 2 file `.docx` báo cáo | M3 – Phỏng vấn | longhh | Có |
| `templates/barem/` | Mẫu barem chấm phỏng vấn (tài liệu, không có code nào đọc) | M3 | longhh | Có |

Vấn đề:

- **Code M1 bị trùng ở 2 nơi và đã lệch nhau.** `ai-service/app` và `services/cv-extraction-ai/app` khác nhau ở các file `core/config.py`, `kb/linker.py`, `kb/store.py`, `services/model_loader.py`. Ngoài ra `kb/extension.py` chỉ có ở bản services. Thư mục `kb/` cũng khác: bản ai-service có script build KB, bản services có `export_system_graph.py`.
- **Thư mục cấp gốc lộn xộn:** `AI/`, `ai-service/`, `services/`, `tools/`, `models/`, `templates/`. Bản trên `dev_hocnv` còn có cả `ai/`, nhưng thư mục này đã bị xoá trên `develop`.
- **Có 3 hệ Knowledge Base kỹ năng riêng:** `ai-service/kb`, `services/cv-extraction-ai/kb` và `tools/build_kb`. Ghi nhận ở đây, nhưng **không** gộp trong đợt này (xem mục 6).
- **`dev_hocnv` đang chậm 2 commit so với `develop`, đồng thời có 7 commit chưa lên `develop`** (training v6.1).

## 2. Mục tiêu và nguyên tắc

Mục tiêu: một thư mục `ai-service/` duy nhất, chia theo 3 module nghiệp vụ. Mỗi module có chủ rõ ràng, và đi một vòng trong repo là thấy hết phần AI.

Nguyên tắc "không ảnh hưởng code người khác":

1. **Module M2 và M3 chỉ được di chuyển nguyên khối bằng `git mv`.** Không sửa logic, không đổi tên file bên trong, không đổi cấu trúc con.
2. **Giữ nguyên hợp đồng chạy:** tên service trong compose (`cv-extraction-ai`, `cvmatch-ai`, `interview-ai`), cổng, biến môi trường (`AI_URL`, `CV_EXTRACTION_URL`, `CVMATCH_URL`) và API. Backend Java không phải sửa.
3. **Tách 2 commit:**
   - Commit A chỉ đổi tên (100% rename), để Git nhận ra rename và các nhánh khác rebase được.
   - Commit B chỉ sửa đường dẫn tham chiếu.
4. **Chỉ hợp nhất code bên trong module M1** (của Hocnv).
5. **File ngoài module mà phải sửa đường dẫn sẽ được liệt kê cụ thể và xin owner duyệt** trong PR.
6. **Không xoá file của người khác, không viết lại lịch sử Git.**

## 3. Cấu trúc đích

```
ai-service/
├── README.md                  # bản đồ: module, owner, cổng, lệnh chạy, test
├── extraction/                # M1 · Hocnv
│   ├── service/               # serving: hợp nhất services/cv-extraction-ai + ai-service/app
│   │   ├── app/  kb/  tests/  checkpoint-v4/  Dockerfile  main.py  requirements.txt
│   ├── training/              # ← ai-service/training
│   ├── eval/                  # ← ai-service/eval
│   ├── kb-builder/            # ← script build KB trong ai-service/kb (books, fetch_sources, build_seed…)
│   ├── notebooks/             # ← ai-service/*.ipynb
│   └── docs/                  # ← AI/DoAn_Module1_TrichXuatCV.docx, AI/Chuong4_Knowledge_Base.docx (cần longhh đồng ý)
├── matching/                  # M2 · nguyenloc
│   ├── service/               # ← services/cvmatch-ai   (git mv nguyên khối)
│   └── kb-builder/            # ← tools/build_kb        (git mv nguyên khối)
├── interview/                 # M3 · longhh
│   ├── service/               # ← AI/                   (git mv nguyên khối, trừ 2 file .docx)
│   └── rubric-templates/      # ← templates/barem
└── models/                    # ← models/ (trọng số, gitignored)
    └── cv-extraction/
```

Bảng đối chiếu đường dẫn cũ → mới:

| Cũ | Mới |
|---|---|
| `services/cv-extraction-ai/` | `ai-service/extraction/service/` |
| `ai-service/app`, `main.py`, `tests/`, `checkpoint-v4/` | hợp nhất vào `ai-service/extraction/service/` |
| `ai-service/training/`, `eval/` | `ai-service/extraction/training/`, `eval/` |
| `ai-service/kb/` (script build) | `ai-service/extraction/kb-builder/` |
| `ai-service/*.ipynb` | `ai-service/extraction/notebooks/` |
| `models/cv-extraction/` | `ai-service/models/cv-extraction/` |
| `services/cvmatch-ai/` | `ai-service/matching/service/` |
| `tools/build_kb/` | `ai-service/matching/kb-builder/` |
| `AI/` | `ai-service/interview/service/` |
| `templates/barem/` | `ai-service/interview/rubric-templates/` |

## 4. Các bước thực hiện

### Phase 0 – Chuẩn bị (Hocnv, 0,5 ngày)

1. Đưa 7 commit của `dev_hocnv` lên `develop` qua PR, hoặc merge `origin/develop` vào `dev_hocnv`, để nhánh refactor bắt đầu từ code mới nhất.
2. Tạo nhánh `hocnv/ai-service-restructure` từ `origin/develop` đã cập nhật.
3. **Thông báo nguyenloc và longhh:**
   - Thời điểm merge PR refactor.
   - Đề nghị merge hoặc đẩy các thay đổi đang làm trong `services/cvmatch-ai`, `tools/build_kb`, `AI/`, `templates/barem` trước thời điểm đó.
   - Trong khoảng 1 ngày từ lúc mở PR đến lúc merge, không push thay đổi vào các thư mục này.
4. Liệt kê nhánh đang mở chạm vào các thư mục trên (`git diff --name-only develop...<nhánh>`), báo cho owner.

### Phase 1 – Hợp nhất M1 (Hocnv, 1–2 ngày, chỉ trong code của mình)

1. `git mv services/cv-extraction-ai ai-service/extraction/service`: lấy bản đang chạy production làm gốc.
2. So từng file khác nhau giữa `ai-service/app` và `service/app` (`config.py`, `linker.py`, `store.py`, `model_loader.py`). Giữ hành vi serving hiện tại, chỉ port những thay đổi nghiên cứu cần thiết. Mỗi file chọn bản nào thì ghi vào PR.
3. Chuyển `training/`, `eval/`, notebook và script build KB sang `ai-service/extraction/` theo bảng ở mục 3. Xoá `ai-service/app` cũ sau khi đã hợp nhất (đây là code của mình).
4. Gộp `tests/`. Sửa import và đường dẫn nội bộ: `BASE_DIR = parents[2]`, `../infra/kg/.env` trong README.
5. Chuyển `models/` thành `ai-service/models/`. Cập nhật `.gitignore`: `ai-service/data/`, `merged_model`, `checkpoint-*/*.safetensors`, `kb/.cache`.
6. Kiểm tra:
   - `pytest` trong `ai-service/extraction/service` pass.
   - `docker compose --profile cv-ai build cv-extraction-ai` thành công.
   - `/api/v1/extract-cv` trả kết quả giống trước trên 3 CV mẫu.

### Phase 2 – Di chuyển M2, M3 (Hocnv thực hiện, owner duyệt; 0,5 ngày)

**Commit A – chỉ đổi tên, không sửa nội dung:**

```bash
git mv services/cvmatch-ai   ai-service/matching/service
git mv tools/build_kb        ai-service/matching/kb-builder
git mv AI                    ai-service/interview/service
git mv templates/barem       ai-service/interview/rubric-templates
```

**Commit B – sửa đường dẫn tham chiếu.** Đây là các file đã tìm thấy:

| File | Sửa gì | Owner cần duyệt |
|---|---|---|
| `docker-compose.yml` | `context: ./AI`, `./services/cv-extraction-ai`, `./services/cvmatch-ai`; volume `./AI/output/...`, `./models/cv-extraction`, `./tools/build_kb/out/snapshot` | Cả nhóm |
| `.gitignore` | Đường dẫn `ai-service/...`, `models/` | – |
| `README.md` (gốc) | Bảng thư mục, lệnh đặt file `.gguf` | – |
| `backend/README.md` | `AI/`, `models/cv-extraction/`, `services/cv-matching-ai` | – |
| `backend/scripts/export-legacy.py:58` | `'AI/data/interview_bank_v2_seed.sql'` | longhh |
| `backend/scripts/smoke-interview.py:31` | `'AI/data/interview_bank_v2.json'` | longhh |
| `docs/Module3_Interview_Flow.md` | 3 đường dẫn `AI/...` | longhh |
| `ai-service/matching/service/.env.example:18`, `README.md:29,44,121` | `../../tools/build_kb/...` → `../kb-builder/...` (chỉ chú thích và lệnh mẫu, không phải code) | **nguyenloc** |
| `ai-service/matching/service/docs/**` | Nhắc `services/cvmatch-ai`, `tools/build_kb` trong tài liệu thiết kế | **nguyenloc tự sửa sau**, không làm trong PR này |
| `ai-service/interview/service/README.md` | Sơ đồ `AI/` | longhh |

Không sửa `docs/diagrams/_v1/**`: đó là ảnh chụp tài liệu cũ, ghi rõ trong README là đường dẫn trước refactor.

### Phase 3 – Kiểm chứng (Hocnv, 0,5 ngày)

- `docker compose config` hợp lệ. `docker compose --profile ai --profile cv-ai build` build được đủ 3 image AI.
- Test từng module tại thư mục mới, với lệnh owner đang dùng:
  - M1: `pytest`.
  - M2: `pytest` trong `matching/service` và `matching/kb-builder`.
  - M3: `pytest tests`.
- Chạy `backend/scripts/smoke-interview.py`. Chạy một luồng upload CV → matching → phỏng vấn qua gateway.
- `git grep -nE "(^|[^-])AI/|services/cv-|services/cvmatch|tools/build_kb|templates/barem"` không còn kết quả ngoài `docs/diagrams/_v1`.
- `git log --follow` trên vài file của M2, M3 vẫn thấy lịch sử cũ.

### Phase 4 – Bàn giao

- PR vào `develop`, reviewer là nguyenloc (M2) và longhh (M3).
- Sau khi merge, mỗi người:
  1. `git pull --rebase` các nhánh đang làm. Git tự áp thay đổi vào đường dẫn mới nhờ commit A là rename thuần.
  2. Tự chuyển file local không nằm trong Git sang chỗ mới: `.venv`, `.env`, trọng số, `dataset`, `out/` của build_kb, `output/` của AI.
- Cập nhật `docs/PLAN_chuc_nang_he_thong.md`, mục 1 (bảng thành phần AI).

## 5. Rủi ro và cách giảm

| Rủi ro | Cách giảm |
|---|---|
| Nhánh đang mở của người khác bị conflict | Chốt thời điểm. Commit A là rename thuần. Owner merge trước. Hướng dẫn rebase. |
| Mất file local (trọng số 12 GB, dataset, `.env`) khi di chuyển | Dùng `git mv` chỉ với file tracked. Liệt kê và tự `mv` file untracked. Không chạy `git clean`. |
| Docker build hỏng vì `COPY` tương đối | Dockerfile dùng đường dẫn tương đối theo context, nên đổi `context` là đủ. Kiểm chứng bằng build ở Phase 3. |
| Hợp nhất M1 làm thay đổi kết quả trích xuất | Lấy bản serving làm gốc. So kết quả trên CV mẫu trước và sau. |
| Đường dẫn cứng trong notebook Colab | Notebook là của M1. Sửa đường dẫn Drive và repo trong cùng Phase 1. |

## 6. Ngoài phạm vi đợt này (cần owner đồng ý, làm sau)

- Gộp 3 hệ Knowledge Base kỹ năng (`extraction/kb`, `extraction/kb-builder`, `matching/kb-builder`) thành một nguồn chung.
- Tách thư viện dùng chung `ai-service/shared/`: chuẩn hoá text tiếng Việt, từ điển kỹ năng.
- Thống nhất cấu trúc bên trong M3 (`src/` phẳng) với M1 và M2 (`app/` hoặc `src/<package>`).
- Thống nhất cách quản lý dependency (requirements.txt hay pyproject) và Python version giữa 3 service.

## 7. Quyết định cần chốt trước khi làm

1. **Di chuyển M2 và M3 ngay trong đợt này, hay chỉ làm Phase 1 (M1) trước?** Khuyến nghị: làm Phase 1 ngay, Phase 2 sau khi nguyenloc và longhh đồng ý thời điểm.
2. **Tên thư mục con:** `service/` + `kb-builder/` như trên, hay giữ nguyên tên gốc (`cvmatch-ai/`, `build_kb/`, `AI/`) để owner dễ nhận ra?
3. **Chuyển `models/` vào `ai-service/models/`?** Việc này đổi chỗ mọi người đặt file `.gguf`.
4. **Hai file `.docx` báo cáo trong `AI/`** chuyển sang `ai-service/extraction/docs/` hay `docs/reports/`?
