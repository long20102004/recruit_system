# M4-SEQ-BE — Ôn tập và chấm phỏng vấn (Backend)

## 1. Thông tin chung

- **Mã biểu đồ:** `M4-SEQ-BE`
- **Loại biểu đồ:** Sequence Diagram (Biểu đồ tuần tự chi tiết)
- **Tên biểu đồ:** Biểu đồ tuần tự chi tiết - Ôn tập và chấm phỏng vấn (Backend)
- **Module:** M4 (Module 3 trong tài liệu repo: Luyện phỏng vấn và chấm điểm v2)
- **Phạm vi kiến trúc:** Microservices — `interview-service` (cổng 8083, Spring Boot 4.1, Java 17, CSDL riêng `hirelens_interview`), kết nối nội bộ tới `recruitment-service` (cổng 8082) qua `ServiceHttpClient` và dịch vụ AI `interview-ai` (cổng 8000, FastAPI) qua `AiScoringClient`.
- **Số lifeline:** 8 lifeline (thỏa mãn ràng buộc $\le 8$).
- **Số message:** 26 message (thỏa mãn ràng buộc $\le 26$).
- **Khung kết hợp:** 1 Combined Fragment `alt` (`submitResult`) với 3 nhánh: 1 luồng chính thành công và 2 luồng ngoại lệ có thật trong mã nguồn.

---

## 2. Kịch bản theo message (khớp 1-1 với `seq`)

### Phần 1: Khởi tạo phiên phỏng vấn (`createSession`)

1. **Frontend gửi yêu cầu tạo phiên:** Client gửi request HTTP `POST /api/interviews/sessions` kèm DTO `CreateSessionRequest(jobId, questionCount=6)` tới phương thức `createSession` của `InterviewController`.
2. **Controller chuyển tiếp yêu cầu sang tầng Service:** `InterviewController` chuyển tiếp DTO sang `interviewService.createSession(request)`. Service xác thực vai trò ứng viên `CANDIDATE` qua `SecurityUtils.requireRole` và lấy mã người dùng hiện tại qua `SecurityUtils.currentUser()`.
3. **Service yêu cầu lấy ngữ cảnh phỏng vấn:** `InterviewService` gọi phương thức `serviceHttpClient.get(url, InterviewContext.class)` với URL truy vấn ngữ cảnh theo `userId`, `jobId` và `applicationId`.
4. **Client nội bộ gửi HTTP request sang recruitment-service:** `ServiceHttpClient` tự động đính kèm shared token bí mật `X-Service-Token` vào header và gửi request HTTP `GET /internal/interview-context?userId={id}&jobId={jobId}` sang `recruitment-service`.
5. **recruitment-service trả về dữ liệu ngữ cảnh:** `InternalRecruitmentController` trích xuất thông tin kỹ năng bắt buộc từ tin tuyển dụng (`job_skills`), kỹ năng ứng viên từ hồ sơ CV (`cv_data`), xác định cấp độ mục tiêu (Intern / Junior / Middle) và trả về đối tượng `InterviewContext`.
6. **ServiceHttpClient nhận và parse dữ liệu ngữ cảnh:** `ServiceHttpClient` parse chuỗi JSON phản hồi thành đối tượng `InterviewContext` và trả về cho `InterviewService`.
7. **Service gọi thuật toán chọn bộ câu hỏi:** `InterviewService` lấy danh sách ID câu hỏi đã làm trong 36 lượt gần đây qua `sessionQuestionRepository.recentQuestionIds()` và gọi `questionSelectionService.select(pool, context, recent, count)` với danh sách câu hỏi hoạt động (`is_active = 1`).
8. **QuestionSelectionService trả về 6 câu hỏi tối ưu:** Thuật toán tính điểm ưu tiên (khớp kỹ năng JD +40, kỹ năng CV +20, khoảng cách đồ thị tri thức `SkillGraph` +8..+16, phạt chênh lệch cấp độ -3/bậc, phạt lặp lại -12) và trả về danh sách 6 câu hỏi đảm bảo đa dạng chủ đề (tối đa 2 câu/chủ đề).
9. **Service khởi tạo phiên và trả về SessionResponse:** `InterviewService` tạo bản ghi `interview_sessions` (trạng thái `CREATED`), tạo 6 bản ghi `interview_session_questions` (thứ tự `questionOrder` từ 1 đến 6) trong CSDL `hirelens_interview`, sau đó đóng gói và trả về `SessionResponse` (với `currentIndex = 0`).
10. **Controller phản hồi phiên phỏng vấn cho Frontend:** `InterviewController` trả về `SessionResponse` qua HTTP 200 cho Frontend để hiển thị câu hỏi phỏng vấn đầu tiên.

### Phần 2: Nộp câu trả lời và chấm điểm AI (`submitResponse`)

11. **Frontend gửi câu trả lời của ứng viên:** Ứng viên soạn nội dung câu trả lời và nhấn gửi, Frontend gửi request HTTP `POST /api/interviews/sessions/{id}/responses` kèm `SubmitResponseRequest(questionId, answerText)` tới `InterviewController.submitResponse`.
12. **Controller chuyển tiếp câu trả lời sang Service:** `InterviewController` gọi `interviewService.submitAndEvaluate(sessionId, request)`. Tại đây, Service thực thi khóa bi quan `sessionRepository.findForUpdate(sessionId)` (`SELECT ... FOR UPDATE`) để ngăn ngừa xung đột ghi đồng thời hoặc gian lận nộp bài đa tab.

#### Khung kết hợp `alt` (`id: "submitResult"`):

- **Nhánh 1 (`guard: "[phiên hợp lệ và AI chấm điểm thành công]"`):**
  13. **Service gọi Client chấm điểm AI:** Trong điều kiện phiên hợp lệ đang diễn ra, Service cập nhật thời điểm `startedAt`, chuyển trạng thái phiên thành `IN_PROGRESS`, lưu câu trả lời vào `interview_responses`, truy xuất barem tiêu chí từ bảng `evaluation_rubrics` qua `rubricRepository.findByQuestionId()`, rồi gọi `aiScoringClient.evaluate(answer, questionText, referenceAnswer, criteria, questionIdLabel)`.
  14. **Client chấm điểm gửi request sang interview-ai:** `AiScoringClient` chuẩn hóa trọng số các tiêu chí rubric (tổng bằng 1.0) qua `normalizeCriteria` và gửi request HTTP `POST /v1/interview/evaluate` với toàn bộ barem tiêu chí và đáp án mẫu sang dịch vụ FastAPI `interview-ai` (cổng 8000).
  15. **interview-ai trả về kết quả chấm điểm định lượng và định tính:** Tiến trình AI tính toán điểm BERTScore Precision/Recall/F1, phân rã mệnh đề rubric coverage, hiệu chỉnh hồi quy Ridge và tạo nhận xét, rồi phản hồi chuỗi JSON kết quả.
  16. **AiScoringClient parse kết quả thành EvaluateResult:** Client kiểm tra mã trạng thái HTTP 200, xác thực tính hợp lệ của điểm số (0–10) và trả về đối tượng `EvaluateResult` cho `InterviewService`.
  17. **Service lưu kết quả đánh giá và cập nhật tiến độ phiên:** `InterviewService` thực thi `saveAiEvaluation`, lưu bản ghi vào bảng `evaluation_results`. Nếu tất cả câu hỏi trong phiên đã có điểm, service cập nhật `session.status = COMPLETED` và `completedAt`. Cuối cùng, service trả về DTO `EvaluationResponse`.
  18. **Controller phản hồi kết quả đánh giá cho Frontend:** `InterviewController` trả về `EvaluationResponse` qua HTTP 200 để Frontend hiển thị giao diện `EvalBlock` (vòng tròn điểm số, chỉ số BERTScore, tiêu chí barem và nhận xét).

- **Nhánh 2 (`guard: "[phiên đã hoàn thành (COMPLETED)]"`):**
  19. **Service phát hiện phiên đã kết thúc trước đó:** Nếu trạng thái phiên truy vấn được là `COMPLETED`, `InterviewService` ném ngay ngoại lệ `ApiException(HttpStatus.CONFLICT, "Session completed; start another practice session")`.
  20. **Hệ thống chuyển đổi ngoại lệ thành HTTP 409 Conflict:** `GlobalExceptionHandler` bắt ngoại lệ `ApiException` và chuyển đổi thành phản hồi HTTP 409 Conflict gửi về cho Client, ngăn chặn việc ghi đè hay nộp bài lặp lại.

- **Nhánh 3 (`guard: "[dịch vụ AI lỗi hoặc mất kết nối]"`):**
  21. **Service gọi Client chấm điểm AI:** Service gửi câu trả lời và barem rubric tới `aiScoringClient.evaluate(...)`.
  22. **Client gửi HTTP POST sang dịch vụ AI:** `AiScoringClient` gửi request HTTP tới endpoint `/v1/interview/evaluate`.
  23. **interview-ai phản hồi lỗi hoặc mất kết nối:** Dịch vụ AI ném lỗi HTTP 500/503 (chưa nạp calibration, BERT crash) hoặc HttpClient bị từ chối kết nối / quá thời gian chờ (read timeout).
  24. **AiScoringClient ném ApiException lỗi kết nối AI:** Do hệ thống thiết lập `fallback-to-rule = false` (không dùng rule giả lập điểm số khi AI lỗi), `AiScoringClient` ném ngay `ApiException(HttpStatus.BAD_GATEWAY)` hoặc `SERVICE_UNAVAILABLE`.
  25. **Service lan truyền ngoại lệ và rollback transaction:** Ngoại lệ `ApiException 502` được lan truyền ra khỏi phương thức `@Transactional submitAndEvaluate`, kích hoạt rollback toàn bộ transaction CSDL (không lưu bản ghi câu trả lời rác hay điểm số dở dang).
  26. **Hệ thống chuyển đổi ngoại lệ thành HTTP 502 Bad Gateway:** `GlobalExceptionHandler` bắt ngoại lệ và trả về phản hồi HTTP 502 Bad Gateway cho Frontend hiển thị thông báo lỗi dịch vụ AI.

---

## 3. Bảng truy vết Lifeline

| STT | Khóa (`key`) | Tên hiển thị (`name`) | Phân loại (`kind`) | Tên lớp (`class`) | Nguồn truy vết trong mã nguồn (`src`) |
|:---:|:---|:---|:---:|:---|:---|
| 1 | `client` | `:client (Frontend)` | object | *(ngoài)* | `source/recruit_system/frontend/src/api/client.ts:125` |
| 2 | `interviewController` | `:InterviewController` | object | `InterviewController` | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/controller/InterviewController.java:14` |
| 3 | `interviewService` | `:InterviewService` | object | `InterviewService` | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:23` |
| 4 | `serviceHttpClient` | `:ServiceHttpClient` | object | `ServiceHttpClient` | `source/recruit_system/backend/common/src/main/java/recruit/demo/client/ServiceHttpClient.java:13` |
| 5 | `recruitmentService` | `:recruitment-service` | object | *(ngoài)* | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/InternalRecruitmentController.java:19` |
| 6 | `questionSelectionService` | `:QuestionSelectionService` | object | `QuestionSelectionService` | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/QuestionSelectionService.java:8` |
| 7 | `aiScoringClient` | `:AiScoringClient` | object | `AiScoringClient` | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/AiScoringClient.java:26` |
| 8 | `interviewAi` | `:interview-ai` | object | *(ngoài)* | `source/recruit_system/AI/src/api.py:205` |

---

## 4. Bảng truy vết Message → File:Dòng

| Seq | Từ (`from`) | Tới (`to`) | Thao tác (`operation`) | Loại (`kind`) | Nguồn truy vết trong mã nguồn (`src`) |
|---:|:---|:---|:---|:---:|:---|
| 1 | `client` | `interviewController` | `createSession(request)` | sync | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/controller/InterviewController.java:24` |
| 2 | `interviewController` | `interviewService` | `createSession(request)` | sync | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/controller/InterviewController.java:25` |
| 3 | `interviewService` | `serviceHttpClient` | `get(url, type)` | sync | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:51` |
| 4 | `serviceHttpClient` | `recruitmentService` | `GET /internal/interview-context` | sync | `source/recruit_system/backend/common/src/main/java/recruit/demo/client/ServiceHttpClient.java:20` |
| 5 | `recruitmentService` | `serviceHttpClient` | `GET /internal/interview-context` | return | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/InternalRecruitmentController.java:50` |
| 6 | `serviceHttpClient` | `interviewService` | `get` | return | `source/recruit_system/backend/common/src/main/java/recruit/demo/client/ServiceHttpClient.java:39` |
| 7 | `interviewService` | `questionSelectionService` | `select(pool, context, recent, count)` | sync | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:68` |
| 8 | `questionSelectionService` | `interviewService` | `select` | return | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/QuestionSelectionService.java:48` |
| 9 | `interviewService` | `interviewController` | `createSession` | return | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:94` |
| 10 | `interviewController` | `client` | `createSession` | return | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/controller/InterviewController.java:25` |
| 11 | `client` | `interviewController` | `submitResponse(id, request)` | sync | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/controller/InterviewController.java:40` |
| 12 | `interviewController` | `interviewService` | `submitAndEvaluate(sessionId, request)` | sync | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/controller/InterviewController.java:42` |
| 13 | `interviewService` | `aiScoringClient` | `evaluate(answer, questionText, referenceAnswer, criteria, questionIdLabel)` | sync | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:169` |
| 14 | `aiScoringClient` | `interviewAi` | `POST /v1/interview/evaluate` | sync | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/AiScoringClient.java:94` |
| 15 | `interviewAi` | `aiScoringClient` | `POST /v1/interview/evaluate` | return | `source/recruit_system/AI/src/api.py:250` |
| 16 | `aiScoringClient` | `interviewService` | `evaluate` | return | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/AiScoringClient.java:106` |
| 17 | `interviewService` | `interviewController` | `submitAndEvaluate` | return | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:128` |
| 18 | `interviewController` | `client` | `submitResponse` | return | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/controller/InterviewController.java:42` |
| 19 | `interviewService` | `interviewController` | `submitAndEvaluate` | return | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:112` |
| 20 | `interviewController` | `client` | `submitResponse` | return | `source/recruit_system/backend/common/src/main/java/recruit/demo/exception/GlobalExceptionHandler.java:18` |
| 21 | `interviewService` | `aiScoringClient` | `evaluate(answer, questionText, referenceAnswer, criteria, questionIdLabel)` | sync | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:169` |
| 22 | `aiScoringClient` | `interviewAi` | `POST /v1/interview/evaluate` | sync | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/AiScoringClient.java:94` |
| 23 | `interviewAi` | `aiScoringClient` | `POST /v1/interview/evaluate` | return | `source/recruit_system/AI/src/api.py:248` |
| 24 | `aiScoringClient` | `interviewService` | `evaluate` | return | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/AiScoringClient.java:99` |
| 25 | `interviewService` | `interviewController` | `submitAndEvaluate` | return | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:123` |
| 26 | `interviewController` | `client` | `submitResponse` | return | `source/recruit_system/backend/common/src/main/java/recruit/demo/exception/GlobalExceptionHandler.java:18` |

---

## 5. Phạm vi và sai khác so với M4-ACT

1. **Phạm vi phân tầng:**
   - `M4-ACT` mô tả toàn diện quy trình hoạt động từ góc nhìn nghiệp vụ tổng thể xuyên suốt 5 làn: `Người dùng` (thao tác giao diện), `Frontend` (xử lý state React), `recruitment-service` (lấy ngữ cảnh JD/CV), `interview-service` (điều phối nghiệp vụ) và `interview-ai` (chấm điểm mô hình).
   - `M4-SEQ-BE` tập trung thể hiện chi tiết luồng tương tác bên trong Backend Spring Boot (`interview-service`), tiếp nhận các request mạng từ `:client (Frontend)` và kết nối ngoại vi sang các microservice khác.
2. **Xử lý kiểm tra dữ liệu đầu vào:**
   - Trong `M4-ACT`, việc kiểm tra câu trả lời không được trống (`dec_answer_valid`) và cảnh báo toast (`act_notify_empty`) diễn ra hoàn toàn phía client (`CandidateInterviewPage.tsx:41`) trước khi gửi request mạng. Do đó, luồng này không sinh ra request HTTP lên máy chủ và không xuất hiện trong `M4-SEQ-BE`.
3. **Lược giản Repository Lifeline:**
   - Để tuân thủ nghiêm ngặt giới hạn $\le 8$ lifeline của đề bài, biểu đồ tập trung vào các ranh giới service và client tích hợp mạng (`InterviewController`, `InterviewService`, `ServiceHttpClient`, `QuestionSelectionService`, `AiScoringClient`).
   - Các thao tác truy cập CSDL nội bộ (như khóa dòng bi quan `InterviewSessionRepository.findForUpdate()`, nạp barem `EvaluationRubricRepository.findByQuestionId()`, lưu kết quả `EvaluationResultRepository.save()`) được thực thi ngầm định trong ranh giới `@Transactional` của `InterviewService` và được diễn giải đầy đủ trong kịch bản mà không cần tạo thêm lifeline giả lập.
4. **Cấu trúc phân nhánh ngoại lệ:**
   - `M4-SEQ-BE` mô phỏng 2 ngoại lệ chính thuộc tầng Backend:
     - Ngoại lệ xung đột phiên (`HttpStatus.CONFLICT` 409) khi ứng viên gửi câu trả lời cho phiên đã kết thúc (`status == COMPLETED`).
     - Ngoại lệ lỗi kết nối hoặc mã lỗi từ dịch vụ AI (`HttpStatus.BAD_GATEWAY` 502), phản ánh đúng việc không dùng fallback rule và rollback transaction CSDL.

---

## 6. Mâu thuẫn giữa tài liệu và mã nguồn

1. **Kiến trúc triển khai ứng dụng:**
   - *Báo cáo đồ án v6:* Mô tả ứng dụng Spring Boot nguyên khối (Monolith) dùng chung một CSDL MySQL duy nhất.
   - *Mã nguồn thực tế (commit `1c96706`):* Đã chuyển hoàn toàn sang **Microservices**: `interview-service` (cổng 8083, CSDL `hirelens_interview`), `recruitment-service` (cổng 8082, CSDL `hirelens_recruitment`) và `interview-ai` (cổng 8000, FastAPI).
   - *Quyết định thiết kế:* Vẽ theo kiến trúc Microservices thực tế trong mã nguồn theo chỉ đạo của kiến trúc sư dự án.
2. **Cơ chế Fallback khi AI gặp sự cố:**
   - *Tài liệu sơ khởi:* Đề xuất có cơ chế rule-based dự phòng để tính điểm cơ bản khi AI ngoại tuyến.
   - *Mã nguồn thực tế (`AiScoringClient.java:46`, `application.yml:44`):* Thuộc tính `fallback-to-rule` được viết cứng là `false`. Khi AI gặp lỗi hoặc không thể kết nối, client ném ngay lỗi HTTP 502/503 và rollback toàn bộ transaction CSDL, tuyệt đối không tính điểm giả lập bằng rule.
3. **Phương pháp chấm điểm và sinh nhận xét:**
   - *Kỳ vọng ban đầu:* Sử dụng mô hình sinh văn bản ngôn ngữ lớn (LLM) để nhận xét tự do.
   - *Mã nguồn thực tế (`AI/src/scoring.py`):* Sử dụng mô hình tất định BERTScore + Barem Rubric phân rã mệnh đề + Hiệu chỉnh hồi quy Ridge Calibration; nhận xét được xây dựng tự động theo bộ quy tắc từ danh sách ý đạt và ý thiếu.

---

## 7. Điểm cần xác nhận (Open Questions)

1. **Lược giản Repository Lifeline:** Biểu đồ tuần tự lược giản các lời gọi nội bộ tới `InterviewSessionRepository`, `InterviewSessionQuestionRepository`, `EvaluationRubricRepository` và `EvaluationResultRepository` để đảm bảo giới hạn $\le 8$ lifeline theo quy định; các thao tác khóa dòng CSDL (`PESSIMISTIC_WRITE`), lưu phiên và lưu kết quả đánh giá vẫn thực sự diễn ra trong `InterviewService`.
2. **Cơ chế xác thực liên service:** Khi `interview-service` gọi `recruitment-service` qua `/internal/interview-context`, hệ thống sử dụng shared token `X-Service-Token` ở cấp độ service và truyền `userId` qua tham số URL thay vì chuyển tiếp JWT của người dùng (Token Relay). Cần xác nhận xem có cần bổ sung chuyển tiếp ngữ cảnh người dùng kép hay không.
