# Feature 015 — Dataset từ ảnh CV thật (intern / fresher) — KẾ HOẠCH

Trạng thái: **chỉ lên kế hoạch**, chưa implement. Bắt đầu khi người dùng gửi ảnh CV.

## Bối cảnh

- Dataset hiện tại phần lớn là CV sinh bằng AI (hồ sơ hư cấu render theo 15 bố cục) + 31 CV thật train, 20 CV thật test.
- Mục tiêu trước mắt: tập trung **intern / fresher**; thay dần dữ liệu AI gen bằng **dữ liệu thật**.
- PDF thật hiện có: ~59 file (`dataset/pdf/`). Ảnh: `dataset/img/` (30 ảnh, sẽ thu thêm).
- Quyết định của người dùng (17/11/2026):
  - Nguồn ảnh: **CV thật có đồng ý** của chủ CV.
  - Dạng ảnh: **ảnh chụp màn hình** (nét, OCR tốt).
  - Số lượng dự kiến: **200–500 ảnh**.
  - Duyệt nhãn: **người dùng tự duyệt**.

## Nguyên tắc dữ liệu

- Ảnh, PDF tái tạo, text, nhãn chỉ nằm trong `dataset/` và `ai-service/data/` (đã gitignore); không commit, không gửi cho dịch vụ/LLM bên ngoài. OCR và model chạy trên máy local.
- Log, báo cáo, tài liệu chỉ ghi số đếm; không đưa nội dung CV thật vào.
- Chia train/dev/test **theo người** (mọi trang, mọi biến thể của một CV nằm cùng một phía).

## Giai đoạn 0 — Kiểm chứng OCR (làm trước, ~1 ngày)

Mục đích: biết dữ liệu từ ảnh có đủ tốt để train hay không, trước khi người dùng mất công thu ảnh.

1. Render 59 PDF thật thành ảnh (pdftoppm, 200–300 dpi).
2. OCR bằng Tesseract 5 `vie+eng` (đã cài). So với lớp chữ gốc của PDF → **tỷ lệ lỗi ký tự (CER)**, riêng lỗi dấu tiếng Việt.
3. Nếu CER > ~2 %: thử PaddleOCR / VietOCR, chọn engine tốt nhất.
4. Chạy v4 trên text OCR và text gốc của cùng CV → so F1 từng trường.

Tiêu chí đạt: CER ≤ 2 % và F1 trên text OCR thấp hơn text gốc không quá ~0,02 ở company / school / skills.

## Giai đoạn 1 — Ảnh → PDF có lớp chữ

- Quy ước tên ảnh: `<mã CV>_p1.png`, `<mã CV>_p2.png`… (ghép các trang của cùng CV).
- OCR lấy từng từ + toạ độ (hOCR), ghi thành PDF: ảnh làm nền + lớp text vô hình đặt đúng vị trí (như ocrmypdf).
- Lấy text bằng **chính bộ trích xuất của backend** (`PdfTextDumpRunner`, mode layout / XY-cut) → text giống hệt lúc serve.
- Script dự kiến: `ai-service/training/ocr/image_to_pdf.py` (+ test với ảnh hư cấu).

## Giai đoạn 2 — Gán nhãn có model hỗ trợ

Vì sao cần: fine-tune học từ cặp (text CV, JSON đúng); JSON đúng không có sẵn. Không dùng nguyên output của v4 làm nhãn vì sẽ dạy lại chính lỗi của v4 — giá trị nằm ở phần người sửa.

1. v4 sinh JSON nháp cho từng CV (local, `?include=raw`).
2. Tự đánh dấu chỗ đáng ngờ: giá trị không có trong text; v3 và v4 khác nhau; công việc thiếu ngày / ngày ngược; mục có tiêu đề trong CV nhưng JSON rỗng.
3. Công cụ duyệt chạy local (web): ảnh CV bên trái, form JSON bên phải, chỗ đáng ngờ tô màu; sửa, thêm, xoá mục; nút "Duyệt" lưu gold + thời điểm duyệt.
4. Lint quy ước nhãn (v3): company không kèm địa điểm/ngày; skills mỗi kỹ năng một phần tử, không tên nhóm; `end_date = null` khi Present; ngày giữ như CV; languages không chứa ngôn ngữ lập trình; số nguyên cho năm / team_size.

Ước lượng: 2–4 phút/CV khi chỉ duyệt + sửa (gõ từ đầu 15–20 phút) → 300 CV ≈ 10–20 giờ. Tập test duyệt kỹ 100 %; train ưu tiên CV có nhiều chỗ bị đánh dấu.

## Giai đoạn 3 — Dataset v6

- Test cố định ~60 CV thật (khoá hash từng mẫu) + dev ~20 CV thật; còn lại train (+ hoán đổi tên công ty/trường).
- Giữ có chọn lọc dữ liệu sinh: bố cục hai cột L11–L15, nhiều công việc, timeline; cân nhắc bỏ 250 CV silver (nhãn LLM, quy ước cũ) — quyết định bằng thử nghiệm có/không.
- Tỷ lệ dữ liệu thật trong train ≥ 50 %.
- Builder in **ma trận độ phủ** intern/fresher và chặn build khi một ô < ngưỡng (vd 30 mẫu):
  - kinh nghiệm: 0 công việc, 1 kỳ thực tập, 2+ công việc; dự án nhiều / ít;
  - học vấn: có GPA, đang học, nhiều trường;
  - chứng chỉ / ngoại ngữ: TOEIC, IELTS, chứng chỉ có ngày;
  - hoạt động / CLB / giải thưởng / học bổng;
  - bố cục: 1 cột, 2 cột, timeline; tiếng Việt / tiếng Anh;
  - ngày tháng: 03/2021, Mar 2021, T3/2021, Hiện tại / Present.

## Giai đoạn 4 — Train và đánh giá

- Train trên Colab như v4 (`training/retrain_qwen3_v2.ipynb`, `RUN_NAME="v6"`), chọn checkpoint theo **F1 trên dev thật** thay vì dev loss.
- So **base, v4, v6** cùng engine (llama.cpp GGUF Q4_K_M), cùng prompt, cùng hậu kiểm bằng `eval_models_colab.ipynb` trên test cố định.
- Chấm trên `raw_profile` (trước chuẩn hoá KB) hoặc chuẩn hoá KB cả nhãn lẫn dự đoán.
- Bộ hồi quy cố định: CV hai cột nhiều trang, CV nhiều công việc ngắn, CV sinh viên không kinh nghiệm, CV timeline.
- Điều kiện chấp nhận v6: không trường nào giảm > 0,03 so với v4; company và skills ≥ v4 trên test cố định.

## Việc sửa đo lường (độc lập, có thể làm sớm)

Phát hiện ngày 17/11/2026: benchmark base–v4 ngày 09/11 chấm v4 trên output đã chuẩn hoá KB (đổi tên kỹ năng/trường) nên thấp giả. Trên 20 CV val synthetic, cùng output v4: school 0,750 → 1,000 và skills 0,717 → 0,970 khi chấm trên `raw_profile`.

So sánh công bằng base – v4 (17/11/2026): cùng 20 CV val synthetic (nhãn silver), cùng llama.cpp GGUF Q4_K_M, prompt v3, sinh nối tiếp + hậu kiểm; base chấm biến thể B, v4 chấm `raw_profile`. Chạy CPU local (`data/real_test/runs/cmp_base_v4_n20`).

| Trường | Base | v4 raw | v4 API mặc định (KB) |
|---|---|---|---|
| company | 0,974 | 0,987 | 0,987 |
| job_title | 1,000 | 1,000 | 1,000 |
| school | 0,952 | 1,000 | 0,750 |
| project | 1,000 | 1,000 | 1,000 |
| skills | 0,907 (41 FP) | 0,970 (6 FP) | 0,717 |
| certificates | 0,943 | 0,930 | 0,930 |
| honours | 0,892 | 0,923 | 0,923 |
| languages | 1,000 | 0,952 | 0,952 |
| email | 1,000 | 0,950 | 0,950 |
| JSON hợp lệ | 20/20 | 20/20 | 20/20 |

Kết luận: tập val synthetic quá dễ để phân biệt (base đã ~0,95); khác biệt chính là base thêm nhiều kỹ năng thừa. Lợi ích của fine-tune cần đo trên CV thật (test cố định).

- Sửa `ai-service/eval/benchmark_base_vs_v4_colab.ipynb`: gọi `?include=raw`, chấm `raw_profile`.
- Thêm `v4` (và các bản sau) vào `eval_models_colab.ipynb`; chạy base trên `test_real`.

## Quyết định bổ sung (17/11/2026)

- **Không giữ** dữ liệu level middle / senior / lead trong train: model mới chỉ phục vụ **intern và fresher**. Dữ liệu sinh được giữ lại (Giai đoạn 3) cũng chỉ lấy hồ sơ level junior / intern; bộ hồi quy và tiêu chí chấp nhận chỉ tính trên CV intern/fresher.
- Tỷ lệ CV tiếng Việt / tiếng Anh: **chưa biết**, người dùng báo khi có dataset; builder sẽ in tỷ lệ thực tế, chưa đặt ngưỡng.
