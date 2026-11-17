# Ghi chú thiết kế - Biểu đồ tuần tự M4-SEQ-AI

## Kịch bản tuần tự

1. `Backend` gửi HTTP `POST /v1/interview/evaluate` với câu trả lời, đáp án tham chiếu và rubric inline.
2. `api` chuẩn hóa trọng số rubric bằng `_normalize_criteria`.
3. `api.evaluate` gọi `scoring.evaluate_question` với nội dung đã ghép thành question.
4. Nếu calibration tồn tại, `scoring` nạp cấu hình bằng `load_calibration`.
5. Nếu thiếu calibration, `load_calibration` phát sinh `FileNotFoundError`.
6. Nhánh ngoại lệ: `api` ánh xạ lỗi thiếu calibration thành HTTP 503 trả về `Backend`; nhánh này dừng luồng chấm.
7. `scoring` yêu cầu `features.bertscore_prf` so khớp câu trả lời với đáp án tham chiếu (mode bertscore).
8. `features` gọi `semantic.score_pairs` để tính BERTScore.
9. `semantic` trả các mảng precision, recall và F1 cho `features`.
10. `scoring` gọi `rubric.evaluate_rubric` để đánh giá tiêu chí.
11. Trong mode bertscore, `rubric` lặp qua phân tích câu trả lời bằng `evidence.evidence_units`.
12. `evidence` trả các mệnh đề (tối đa 24) về `rubric`.
13. `rubric` trả độ phủ, kết quả từng tiêu chí, danh sách ý đạt/thiếu về `scoring`.
14. `scoring` tính điểm hiệu chỉnh bằng `predict_score`.
15. `scoring` kết hợp điểm mô hình với độ phủ rubric bằng `combine_model_and_rubric`.
16. `scoring` tạo nhận xét bằng `build_comment`.
17. `scoring.evaluate_question` trả dict kết quả về `api`.
18. `api` dựng `EvaluateResponse` và trả HTTP thành công về `Backend`.

## Truy vết message

| Seq | Message | Nguồn |
|---:|---|---|
| 1 | HTTP POST `/v1/interview/evaluate` | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/AiScoringClient.java:85` |
| 2 | `_normalize_criteria` | `source/recruit_system/AI/src/api.py:98` |
| 3 | `evaluate_question` | `source/recruit_system/AI/src/api.py:222` |
| 4 | `load_calibration` thành công | `source/recruit_system/AI/src/scoring.py:81` |
| 5 | Thiếu calibration / `FileNotFoundError` | `source/recruit_system/AI/src/scoring.py:17` |
| 6 | HTTP 503 | `source/recruit_system/AI/src/api.py:238` |
| 7 | `bertscore_prf` | `source/recruit_system/AI/src/scoring.py:88` |
| 8 | `score_pairs` | `source/recruit_system/AI/src/features.py:39` |
| 9 | Trả các vector BERTScore | `source/recruit_system/AI/src/semantic.py:20` |
| 10 | `evaluate_rubric` | `source/recruit_system/AI/src/scoring.py:92` |
| 11 | `evidence_units` | `source/recruit_system/AI/src/rubric.py:35` |
| 12 | Trả các mệnh đề | `source/recruit_system/AI/src/evidence.py:14` |
| 13 | Kết quả rubric | `source/recruit_system/AI/src/rubric.py:71` |
| 14 | `predict_score` | `source/recruit_system/AI/src/scoring.py:30` |
| 15 | `combine_model_and_rubric` | `source/recruit_system/AI/src/scoring.py:37` |
| 16 | `build_comment` | `source/recruit_system/AI/src/scoring.py:46` |
| 17 | Trả dict kết quả | `source/recruit_system/AI/src/scoring.py:127` |
| 18 | Trả `EvaluateResponse` | `source/recruit_system/AI/src/api.py:250` |

## Đối chiếu và giới hạn

- Phạm vi là phía interview-ai FastAPI; request từ backend chỉ là biên vào, không mô tả xử lý phía Spring.
- Luồng chọn rubric inline là cách backend gửi barem từ DB; nhánh `question_id` không đưa vào sơ đồ để giữ trọng tâm module và giới hạn phần tử.
- So với M4-ACT: biểu đồ hoạt động mô tả xuyên frontend/interview-service/recruitment-service và cả vòng đời phiên; sequence này chỉ chi tiết hóa phần AI, từ HTTP request chấm đến response. Không mô tả chọn câu hỏi, lưu phiên/kết quả hay giao diện.
- Lưu ý: M4-CLS-AI khai báo `evaluate_question`, `bertscore_prf`, `score_pairs`, `evaluate_rubric`, `evidence_units`, `load_calibration`, `predict_score`, `combine_model_and_rubric`, `build_comment` và `_normalize_criteria`; các message tương ứng khớp các operation đó.
- `Backend` không thuộc các lớp AI trong M4-CLS-AI; được giữ như lifeline biên bên gọi theo yêu cầu nhiệm vụ.

## Mâu thuẫn

- Không phát hiện mâu thuẫn giữa source AI và M4-ACT về luồng chấm. M4-ACT là luồng mức hệ thống còn biểu đồ này là phần cắt chi tiết AI.
