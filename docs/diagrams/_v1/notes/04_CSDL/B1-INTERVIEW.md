# B1-INTERVIEW — Thiết kế CSDL interview-service

## Phạm vi và nguồn

Schema cuối của `hirelens_interview`, áp dụng các thay đổi DDL theo thứ tự V1 → V4. V2 chỉ chèn dữ liệu mẫu nên bị bỏ qua. V3 chỉ cập nhật dữ liệu và default `max_score`; giá trị default cuối vẫn là `10.00`. V4 bổ sung cột cho ba bảng hiện có.

## Bảng truy vết

| Bảng | Nguồn cấu trúc |
|---|---|
| `interview_questions` | `source/recruit_system/backend/interview-service/src/main/resources/db/migration/V1__schema.sql:1-13`; cột V4 tại `V4__interview_bank_and_assessment.sql:2-4` |
| `evaluation_rubrics` | `.../V1__schema.sql:15-25`; cột V4 tại `.../V4__interview_bank_and_assessment.sql:5` |
| `interview_sessions` | `.../V1__schema.sql:27-41`; cột V4 tại `.../V4__interview_bank_and_assessment.sql:9` |
| `interview_session_questions` | `.../V1__schema.sql:43-53` |
| `interview_responses` | `.../V1__schema.sql:55-64` |
| `model_versions` | `.../V1__schema.sql:66-76` |
| `evaluation_results` | `.../V1__schema.sql:78-97`; cột V4 tại `.../V4__interview_bank_and_assessment.sql:6-8` |

## Quan hệ

Sáu quan hệ trong spec đều là FK DDL thật: `evaluation_rubrics.question_id`, hai FK của `interview_session_questions`, `interview_responses.session_question_id`, cùng hai FK của `evaluation_results`. Cột `model_version_id` nullable và FK `ON DELETE SET NULL`; các FK còn lại khai báo `ON DELETE CASCADE`.

Các cột `created_by`, `candidate_user_id`, `candidate_id`, `job_id`, `application_id`, `recruiter_user_id` không có FK trong DDL và tham chiếu dữ liệu thuộc service khác (identity/recruitment); không vẽ relation.

## Khác biệt so với `docs/schema.dbml`

- DBML mô tả toàn hệ thống (18 bảng), không riêng interview-service; B1 chỉ gồm 7 bảng thuộc CSDL interview.
- DBML mô tả `interview_sessions` thiếu `candidate_user_id`, `job_title` (có ở V1) và `recruiter_user_id` (V4); ngược lại hai cột V1 này không có trong DBML.
- DBML thiếu các cột V4: `interview_questions.external_key`, `skill`, `seniority`, `source`; `evaluation_rubrics.reference_answers`, `misconceptions`; `interview_sessions` có thêm `recruiter_user_id`; `evaluation_results.scoring_mode`, `scoring_model_version`, `criterion_results`, `coverage_score`.
- DBML không ghi cột `candidate_user_id`, `job_title` trong sessions; các cột này nullable được xác định theo DDL: `candidate_user_id` NOT NULL, `job_title` NULL.
- DBML biểu diễn `evaluation_results.model_version_id` và `response_id` là tham chiếu; cả hai thực sự là FK trong migration. DBML còn ghi tham chiếu chéo tới các bảng service khác nhưng DDL interview không khai báo các FK ấy.
- Tên database `hirelens_interview` xác định từ cấu hình service; cấu trúc ở đây chỉ lấy từ migration.

## Mâu thuẫn tài liệu–source

`docs/schema.dbml` ghi chú chung “Cơ sở dữ liệu không còn khóa ngoại” và các `Ref` là kiểm tra trong mã; điều này không khớp migration interview-service V1, nơi có sáu FK thật. Theo yêu cầu, spec ưu tiên DDL và vẽ các FK trên dưới dạng quan hệ vật lý.

`docs/Module3_Interview_Flow.md` cũng có điểm không đồng nhất với schema V4: phần mô tả nói `evaluation_results` giữ coverage, metric và model, phù hợp với các cột mới; tuy nhiên tài liệu không liệt kê đầy đủ tên cột DDL. Một mô tả “candidate” trong flow dùng ngữ nghĩa ứng viên, còn schema thực lưu cả `candidate_user_id` và `candidate_id`; migration không giải thích rõ hai ID này khác nhau thế nào.

## Open questions

Không có câu hỏi cần thiết để biểu diễn cấu trúc DDL. Ý nghĩa/định danh chính xác của `candidate_user_id` so với `candidate_id` không được DDL giải thích; để nguyên tên và kiểu, không suy diễn.
