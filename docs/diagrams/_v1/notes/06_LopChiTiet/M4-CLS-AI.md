# Ghi chú thiết kế — M4-CLS-AI

## Vai trò lớp và luồng gọi chính

- `api` (`AI/src/api.py:35-43`) khai báo ứng dụng FastAPI; route `evaluate` (`:205-250`) nhận `EvaluateRequest`, chọn barem truyền trực tiếp hoặc câu hỏi tra theo ID, gọi module `scoring`, rồi đóng gói kết quả thành `EvaluateResponse`.
- `EvaluateRequest` và `CriterionIn` (`AI/src/api.py:54-95`) là mô hình đầu vào Pydantic: kiểm tra cấu trúc, giới hạn dữ liệu, và xác nhận có ID hoặc bộ reference/rubric inline. `_normalize_criteria` chuẩn hóa trọng số trước khi chấm.
- `EvaluateResponse` (`AI/src/api.py:117-132`) là mô hình đầu ra Pydantic cho điểm, coverage, nhận xét, kết quả từng tiêu chí và tùy chọn debug.
- `scoring` (`AI/src/scoring.py:62-127`) điều phối `evaluate_question`: tính P/R/F1, dựng feature, đánh giá rubric, dự đoán calibration score, kết hợp điểm rubric và tạo nhận xét. `evaluate_by_id` (`:165-179`) tra câu hỏi rồi chuyển tiếp cùng luồng.
- `features` (`AI/src/features.py:31-62`) tính BERTScore và feature row; `semantic` (`AI/src/semantic.py:11-27`) tạo BERTScorer và tính cặp điểm. `rubric` (`AI/src/rubric.py:28-74`) đánh giá tiêu chí; `evidence` (`AI/src/evidence.py:14-54`) tách mệnh đề và thu thập bằng chứng cục bộ; `coverage` (`AI/src/coverage.py:10-37`) xử lý đối chiếu từ khóa, xung đột và coverage. `io_utils` (`AI/src/io_utils.py:17-25`) chỉ tham gia nhánh tra câu hỏi theo ID.
- Luồng chính theo ACT: HTTP `POST /v1/interview/evaluate` → `api.evaluate` → `scoring.evaluate_question` → `features.bertscore_prf` / `features.build_feature_row` và `rubric.evaluate_rubric` → `semantic.score_pairs` và hàm evidence/coverage → `scoring.predict_score`, `combine_model_and_rubric`, `build_comment` → `EvaluateResponse`. Nếu request chỉ có `question_id`, `scoring.evaluate_by_id` dùng `io_utils.questions_by_id` trước khi vào scoring.

## Pattern thực sự có trong source

- **DTO / validation model:** `EvaluateRequest`, `CriterionIn`, `EvaluateResponse` kế thừa Pydantic `BaseModel` (`AI/src/api.py:54-61`, `:64-95`, `:117-132`). Ranh giới HTTP có cấu trúc xác thực rõ; HireLens có thể truyền rubric từ DB của interview-service mà vẫn kiểm tra kiểu/giới hạn trước khi chạy mô hình, và trả cấu trúc kết quả ổn định.
- **Separation of concerns theo module (pipeline/Facade mức module):** `api.evaluate` là điểm vào HTTP (`AI/src/api.py:205-250`), `scoring.evaluate_question` điều phối các bước (`AI/src/scoring.py:62-127`), còn `features`, `rubric`, `evidence`, `coverage`, `semantic` chuyên trách từng phần (`AI/src/features.py:31`, `AI/src/rubric.py:28`, `AI/src/evidence.py:14`, `AI/src/coverage.py:22`, `AI/src/semantic.py:20`). Với HireLens, tách rubric evidence khỏi điểm toàn câu làm luồng chấm có thể giải thích điểm thiếu/đạt thay vì chỉ trả điểm tổng.
- **Singleton/cache theo tiến trình:** `semantic.get_scorer` dùng `@lru_cache(maxsize=1)` (`AI/src/semantic.py:11-18`), `scoring.load_calibration` dùng cache (`AI/src/scoring.py:16-24`), và `meaning._model` cũng cached (`AI/src/meaning.py:16-20`, nhánh finetune). Trong mode BERTScore của luồng này, cache scorer tránh khởi tạo lại mô hình nặng cho mỗi câu; cache calibration tránh đọc file cấu hình nhiều lần.
- **Đồng bộ truy cập tài nguyên dùng chung:** `semantic.score_pairs` dùng `threading.RLock` quanh scorer (`AI/src/semantic.py:8`, `:20-27`). Điều này tuần tự hóa truy cập scorer được cache khi request đồng thời, giảm nguy cơ tranh chấp trên đối tượng mô hình dùng chung.

## Truy vết và mâu thuẫn

| Thành phần | Nguồn |
|---|---|
| API FastAPI, route evaluate | `source/recruit_system/AI/src/api.py:35-43`, `:205-250` |
| Request và CriterionIn | `source/recruit_system/AI/src/api.py:54-95` |
| Response | `source/recruit_system/AI/src/api.py:117-132` |
| Scoring/calibration | `source/recruit_system/AI/src/scoring.py:17-43`, `:62-127` |
| Feature/BERTScore | `source/recruit_system/AI/src/features.py:31-62` |
| Rubric/evidence/coverage | `source/recruit_system/AI/src/rubric.py:28-74`, `source/recruit_system/AI/src/evidence.py:14-54`, `source/recruit_system/AI/src/coverage.py:10-37` |
| Semantic scorer | `source/recruit_system/AI/src/semantic.py:8-27` |
| Lookup theo ID | `source/recruit_system/AI/src/io_utils.py:17-25` |

Không phát hiện mâu thuẫn docs–source trong phạm vi AI được đưa vào biểu đồ. Luồng M4-ACT ghi scoring có Ridge calibration; code route dùng mode mặc định `bertscore` (`AI/src/api.py:26`, `:207`) và hàm `evaluate_question` dùng calibration cho mode này (`AI/src/scoring.py:81-95`). API còn hỗ trợ mode khác, nhưng biểu đồ giới hạn vào luồng đánh giá được ACT yêu cầu.
