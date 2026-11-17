# Ghi chú thiết kế - Biểu đồ lớp chi tiết M4-CLS-BE (Backend)

## 1. Thông tin chung

- **Mã biểu đồ:** `M4-CLS-BE`
- **Loại biểu đồ:** Class Diagram (Biểu đồ lớp chi tiết)
- **Tên biểu đồ:** Biểu đồ lớp chi tiết - Ôn tập và chấm phỏng vấn (Backend)
- **Module:** M4 (Module 3 trong tài liệu repo: Luyện phỏng vấn và chấm điểm v2)
- **Phạm vi kiến trúc:** Microservices — `interview-service` (cổng 8083, Spring Boot 4.1, Java 17, CSDL riêng `hirelens_interview`), thư viện dùng chung `backend/common`, kết nối nội bộ tới `recruitment-service` (cổng 8082) và dịch vụ AI `interview-ai` (cổng 8000, FastAPI).
- **Phân tầng:** Mô hình MVC (Model – View – Controller) với 3 Package chính:
  - `View`: 4 Data Transfer Objects (DTO) giao tiếp qua API REST.
  - `Controller`: 1 REST Controller điều phối tiếp nhận request.
  - `Model`: 4 Service/Client nghiệp vụ & tích hợp, 4 Repository truy xuất dữ liệu JPA, 5 Entity thực thể ánh xạ CSDL.
- **Tổng số lớp/giao diện:** 18 lớp (đúng giới hạn $\le 18$ lớp của đề bài).

---

## 2. Diễn giải vai trò từng lớp

### 2.1. Tầng View (Data Transfer Objects — DTO)

1. **`CreateSessionRequest`** (`InterviewDtos.java:27`):
   - **Vai trò:** DTO nhận dữ liệu đầu vào khi ứng viên yêu cầu tạo phiên phỏng vấn mới.
   - **Thuộc tính:** `jobId` (mã tin tuyển dụng tùy chọn), `applicationId` (mã đơn ứng tuyển tùy chọn), `questionIds` (danh sách ID câu hỏi chọn thủ công nếu có), `questionCount` (số lượng câu hỏi yêu cầu, mặc định 6 câu).
   - **Đặc điểm:** Record bất biến, đóng gói dữ liệu request trước khi đi vào Controller.

2. **`SessionResponse`** (`InterviewDtos.java:39`):
   - **Vai trò:** DTO phản hồi chi tiết phiên phỏng vấn trả về cho Frontend hiển thị.
   - **Thuộc tính:** `id` (mã phiên), `status` (trạng thái phiên `CREATED`/`IN_PROGRESS`/`COMPLETED`), `currentIndex` (vị trí câu hỏi hiện tại đang phỏng vấn), `jobId`, `jobTitle` (tiêu đề tin tuyển dụng hoặc "Practice Interview"), `createdAt` (thời điểm tạo phiên).

3. **`SubmitResponseRequest`** (`InterviewDtos.java:53`):
   - **Vai trò:** DTO tiếp nhận câu trả lời cho một câu hỏi cụ thể trong phiên.
   - **Thuộc tính:** `questionId` (mã câu hỏi được trả lời, ràng buộc `@NotNull`), `answerText` (nội dung câu trả lời của ứng viên, ràng buộc `@NotBlank`, tối đa 4.000 ký tự qua `@Size(max=4000)`).

4. **`EvaluationResponse`** (`InterviewDtos.java:59`):
   - **Vai trò:** DTO trả về kết quả chấm điểm chi tiết của dịch vụ AI sau khi đánh giá câu trả lời.
   - **Thuộc tính:** `responseId`, `questionId`, `predictedScore` (điểm số dự đoán thang 0–10), `scoreScale` ("0-10"), `coveredPoints` (danh sách ý đạt), `missingPoints` (danh sách ý thiếu/cần cải thiện), `comment` (nhận xét tự động), `bertscoreF1` (chỉ số tương đồng toàn câu F1), `coverageScore` (tỷ lệ độ phủ tiêu chí barem 0.0–1.0).

### 2.2. Tầng Controller

5. **`InterviewController`** (`InterviewController.java:14`):
   - **Vai trò:** REST Controller công khai của `interview-service` (prefix `/api/interviews`), tiếp nhận yêu cầu từ API Gateway Nginx.
   - **Thuộc tính:** `interviewService` (inject `InterviewService`).
   - **Phương thức chính:**
     - `createSession(CreateSessionRequest)` (`:24`): Nhận request tạo phiên qua `POST /api/interviews/sessions`, trả về `SessionResponse`.
     - `getSession(Integer)` (`:35`): Truy vấn trạng thái phiên và câu hỏi qua `GET /api/interviews/sessions/{id}`, trả về `SessionResponse`.
     - `submitResponse(Integer, SubmitResponseRequest)` (`:40`): Nhận câu trả lời qua `POST /api/interviews/sessions/{id}/responses`, gọi service chấm điểm và trả về `EvaluationResponse`.

### 2.3. Tầng Model — Service & Client

6. **`InterviewService`** (`InterviewService.java:23`):
   - **Vai trò:** Lớp dịch vụ trung tâm (Core Domain Service & Facade) điều phối toàn bộ vòng đời phiên ôn tập: kiểm tra quyền ứng viên (`SecurityUtils`), lấy ngữ cảnh từ `recruitment-service`, điều phối chọn câu hỏi, quản lý transaction CSDL, khóa phiên chống xung đột ghi (`findForUpdate`), chuẩn hóa barem rubric và gọi AI chấm điểm.
   - **Thuộc tính:** Inject 4 Repository (`sessionRepository`, `sessionQuestionRepository`, `evaluationResultRepository`, `rubricRepository`), 2 HTTP Client (`aiScoringClient`, `serviceHttp`) và 1 Service thuật toán (`questionSelection`).
   - **Phương thức chính:** `createSession()`, `getSession()`, `submitAndEvaluate()`, `evaluate()`, `saveAiEvaluation()`.

7. **`QuestionSelectionService`** (`QuestionSelectionService.java:8`):
   - **Vai trò:** Thực thi thuật toán chọn câu hỏi tất định theo ngữ cảnh tin tuyển dụng và hồ sơ CV của ứng viên.
   - **Thuộc tính:** `graph` (đối tượng Singleton `SkillGraph.shared()` từ `backend/common`).
   - **Phương thức chính:**
     - `select(pool, context, recent, count)` (`:26`): Tính điểm ưu tiên cho từng câu hỏi dựa trên: khớp kỹ năng JD (+40), khớp kỹ năng CV (+20), khoảng cách tri thức trên SkillGraph (+8 đến +16), phạt chênh lệch cấp độ thâm niên (-3/bậc), phạt lặp lại câu hỏi gần đây (-12), khống chế tối đa 2 câu/chủ đề.
     - `graphScore(required, candidate, skill)` (`:51`): Tính khoảng cách ngữ nghĩa giữa kỹ năng câu hỏi với tập kỹ năng đã biết.

8. **`AiScoringClient`** (`AiScoringClient.java:26`):
   - **Vai trò:** HTTP Client Adapter giao tiếp với dịch vụ AI chuyên biệt FastAPI (`interview-ai`).
   - **Thuộc tính:** `appProperties` (cấu hình URL, timeout, chế độ AI), `objectMapper` (serialize/deserialize JSON).
   - **Phương thức chính:**
     - `evaluate(answer, questionText, referenceAnswer, criteria, questionIdLabel)` (`:38`): Chuẩn hóa trọng số tiêu chí (tổng bằng 1.0), gửi request HTTP POST tới `/v1/interview/evaluate`, nhận kết quả và bóc tách thành `EvaluateResult`. Tuyệt đối không fallback sang tính điểm giả lập khi AI lỗi (ném ngay `ApiException` 502/503).
     - `normalizeCriteria(criteria)` (`:120`): Chuẩn hóa trọng số rubric về khoảng [0, 1].

9. **`ServiceHttpClient`** (`ServiceHttpClient.java:13` trong `backend/common`):
   - **Vai trò:** Generic HTTP Client dùng chung trong toàn bộ hệ sinh thái microservices của HireLens để thực hiện các cuộc gọi Service-to-Service nội bộ.
   - **Thuộc tính:** `mapper` (Jackson ObjectMapper), `token` (`app.services.token` nạp từ biến môi trường `SERVICE_TOKEN`), `client` (`java.net.http.HttpClient` với connection timeout 3 giây).
   - **Phương thức chính:** `get(url, type)` (`:20`), `exchange(method, url, body, type)` (`:22`). Tự động đính kèm header `X-Service-Token` để vượt qua `InternalAccessFilter` của service đích.

### 2.4. Tầng Model — Repository (Spring Data JPA)

10. **`InterviewSessionRepository`** (`InterviewSessionRepository.java:8`):
    - **Vai trò:** Giao diện truy xuất bảng `interview_sessions`.
    - **Phương thức đặc biệt:** `findForUpdate(Integer id)` (`:13`): Truy vấn với khóa bi quan `@Lock(LockModeType.PESSIMISTIC_WRITE)` (`SELECT ... FOR UPDATE`), đảm bảo chỉ một tiến trình được cập nhật trạng thái phiên và nộp bài tại một thời điểm, ngăn chặn gian lận hoặc xung đột đa tab.

11. **`InterviewSessionQuestionRepository`** (`InterviewSessionQuestionRepository.java:11`):
    - **Vai trò:** Giao diện truy xuất bảng `interview_session_questions`.
    - **Phương thức chính:**
      - `findBySessionIdOrdered(sessionId)` (`:19`): Lấy danh sách câu hỏi của phiên sắp xếp theo thứ tự `question_order ASC` kết hợp `JOIN FETCH sq.question`.
      - `recentQuestionIds(userId, page)` (`:22`): Lấy danh sách ID các câu hỏi ứng viên đã làm trong 36 lượt gần nhất để áp dụng hình phạt trùng lặp câu hỏi.
      - `findBySessionIdAndQuestionId(sessionId, questionId)` (`:24`): Kiểm tra tính hợp lệ của câu hỏi trong phiên đang làm.

12. **`EvaluationResultRepository`** (`EvaluationResultRepository.java:8`):
    - **Vai trò:** Giao diện truy xuất bảng `evaluation_results`.
    - **Phương thức chính:** `findByResponseId(Integer responseId)` (`:9`): Tra cứu kết quả đánh giá AI tương ứng với bản ghi câu trả lời của ứng viên.

13. **`EvaluationRubricRepository`** (`EvaluationRubricRepository.java:8`):
    - **Vai trò:** Giao diện truy xuất bảng `evaluation_rubrics`.
    - **Phương thức chính:** `findByQuestionId(Integer questionId)` (`:9`): Tải toàn bộ danh sách tiêu chí chấm, trọng số, từ khóa gợi ý và đáp án mẫu của một câu hỏi phục vụ chấm AI.

### 2.5. Tầng Model — Entity (JPA Domain Model)

14. **`InterviewSession`** (`InterviewSession.java:16`):
    - **Vai trò:** Thực thể trung tâm đại diện cho một phiên luyện phỏng vấn của ứng viên.
    - **Thuộc tính:** `id`, `candidateId`, `candidateUserId`, `jobId`, `jobTitle`, `title`, `status` (`SessionStatus`: `CREATED`, `IN_PROGRESS`, `COMPLETED`), `startedAt`, `completedAt`, `createdAt`.
    - **Quan hệ:** Sở hữu danh sách câu hỏi phiên (`InterviewSessionQuestion`) qua quan hệ Composition 1-n.

15. **`InterviewSessionQuestion`** (`InterviewSessionQuestion.java:15`):
    - **Vai trò:** Thực thể liên kết giữa phiên phỏng vấn và câu hỏi trong ngân hàng đề.
    - **Thuộc tính:** `id`, `session` (`InterviewSession`), `question` (`InterviewQuestion`), `questionOrder` (thứ tự câu trong phiên từ 1 đến 6), `maxScore` (điểm tối đa của câu, mặc định 10.0).

16. **`InterviewResponse`** (`InterviewResponse.java:16`):
    - **Vai trò:** Thực thể lưu trữ câu trả lời của ứng viên cho một câu hỏi trong phiên.
    - **Thuộc tính:** `id`, `sessionQuestion` (`InterviewSessionQuestion`, `@OneToOne`), `answerText` (nội dung câu trả lời), `submittedAt` (thời điểm nộp), `status` ("SUBMITTED").

17. **`EvaluationResult`** (`EvaluationResult.java:20`):
    - **Vai trò:** Thực thể lưu trữ toàn bộ dữ liệu định lượng và định tính thu được từ tiến trình AI chấm điểm.
    - **Thuộc tính:** `id`, `response` (`InterviewResponse`, `@OneToOne`), `evaluationMethod` ("BERTSCORE_RUBRIC"), `bertscorePrecision`, `bertscoreRecall`, `bertscoreF1`, `predictedScore` (điểm số kết hợp 0–10), `feedback` (nhận xét tự động), `strengths` (danh sách ý đạt dạng JSON), `missingPoints` (danh sách ý thiếu dạng JSON), `coverageScore` (độ phủ rubric), `evaluatedAt`.

18. **`EvaluationRubric`** (`EvaluationRubric.java:20`):
    - **Vai trò:** Thực thể định nghĩa barem tiêu chí chấm điểm chuyên biệt cho từng câu hỏi phỏng vấn.
    - **Thuộc tính:** `id`, `criterionName` (tên tiêu chí), `criterionDescription` (diễn giải tiêu chí), `weight` (trọng số tiêu chí), `expectedKeywords` (danh sách từ khóa bắt buộc/gợi ý dạng JSON), `referenceAnswers` (các cách diễn đạt chuẩn tham khảo dạng JSON), `misconceptions` (các ngộ nhận sai phổ biến cần phát hiện dạng JSON).

---

## 3. Các luồng gọi chính (Main Execution Flows)

### 3.1. Luồng 1: Khởi tạo phiên phỏng vấn (`createSession`)

1. Frontend gửi yêu cầu `POST /api/interviews/sessions` kèm `CreateSessionRequest(jobId, questionCount=6)` tới `InterviewController.createSession`.
2. `InterviewController` chuyển tiếp request cho `InterviewService.createSession`.
3. `InterviewService` xác minh quyền `CANDIDATE` qua `SecurityUtils.requireRole` và lấy mã định danh người dùng qua `SecurityUtils.currentUser()`.
4. `InterviewService` sử dụng `ServiceHttpClient.get` gửi request HTTP nội bộ kèm header `X-Service-Token` sang `recruitment-service` tại endpoint `/internal/interview-context?userId={id}&jobId={jobId}` để lấy DTO `ServiceDtos.InterviewContext` (chứa kỹ năng JD, kỹ năng CV và cấp độ thâm niên).
5. `InterviewService` gọi `sessionQuestionRepository.recentQuestionIds(userId, PageRequest.of(0, 36))` để lấy các câu hỏi đã làm gần đây.
6. `InterviewService` gọi `QuestionSelectionService.select`:
   - Lọc các câu hỏi đang kích hoạt (`is_active = 1`, `source = 'synthetic-ai-v2'`).
   - Tính toán điểm ưu tiên kết hợp kỹ năng JD, kỹ năng CV, khoảng cách đồ thị `SkillGraph.shared().distance()`, phạt chênh lệch cấp độ và phạt lặp lại.
   - Chọn ra 6 câu hỏi tối ưu thỏa mãn đa dạng chủ đề (tối đa 2 câu/chủ đề).
7. `InterviewService` khởi tạo thực thể `InterviewSession` (trạng thái `CREATED`) và lưu qua `sessionRepository.save(session)`.
8. `InterviewService` duyệt qua 6 câu hỏi, tạo 6 thực thể `InterviewSessionQuestion` với `questionOrder` từ 1 đến 6 và lưu qua `sessionQuestionRepository.save()`.
9. `InterviewService` ánh xạ `InterviewSession` thành `SessionResponse` và trả về cho Controller để phản hồi Frontend.

### 3.2. Luồng 2: Xem chi tiết phiên và lấy câu hỏi (`getSession`)

1. Frontend gửi `GET /api/interviews/sessions/{id}` tới `InterviewController.getSession`.
2. `InterviewController` gọi `InterviewService.getSession(id)`.
3. `InterviewService` truy vấn `sessionRepository.findById(id)` và xác thực quyền sở hữu (`ensureCanAccess`: đúng `candidateUserId` hoặc vai trò `ADMIN`/`RECRUITER` liên quan).
4. `InterviewService` truy vấn danh sách câu hỏi phiên qua `sessionQuestionRepository.findBySessionIdOrdered(id)`.
5. Service xác định chỉ số câu hỏi hiện tại `currentIndex` (vị trí câu hỏi đầu tiên chưa được chấm điểm) và đóng gói vào `SessionResponse` trả về cho Frontend.

### 3.3. Luồng 3: Nộp câu trả lời và chấm điểm AI (`submitResponse` / `submitAndEvaluate`)

1. Frontend gửi `POST /api/interviews/sessions/{id}/responses` kèm `SubmitResponseRequest(questionId, answerText)` tới `InterviewController.submitResponse`.
2. Controller gọi `InterviewService.submitAndEvaluate(sessionId, request)`.
3. `InterviewService` thực thi `sessionRepository.findForUpdate(sessionId)` với khóa bi quan (`PESSIMISTIC_WRITE`) nhằm ngăn chặn tình trạng race condition khi người dùng nhấn submit lặp lại hoặc mở nhiều tab.
4. Service kiểm tra trạng thái phiên: nếu phiên đã ở trạng thái `COMPLETED` thì ném ngay ngoại lệ `ApiException(HttpStatus.CONFLICT)`.
5. Service tìm câu hỏi tương ứng trong phiên qua `sessionQuestionRepository.findBySessionIdAndQuestionId(sessionId, questionId)`.
6. Service cập nhật `startedAt` (nếu chưa có), chuyển trạng thái phiên thành `IN_PROGRESS`, khởi tạo `InterviewResponse` với nội dung trả lời và lưu qua `responseRepository.save(response)`.
7. Service truy xuất toàn bộ barem tiêu chí của câu hỏi qua `rubricRepository.findByQuestionId(question.getId())` và chuẩn hóa thành danh sách `AiScoringDtos.CriterionIn`.
8. Service gọi `AiScoringClient.evaluate(answerText, questionText, referenceAnswer, criteria, questionIdLabel)`:
   - `AiScoringClient` chuẩn hóa trọng số tiêu chí tổng bằng 1.0 (`normalizeCriteria`).
   - Đóng gói JSON và gửi request HTTP POST tới `interview-ai` tại endpoint `/v1/interview/evaluate`.
   - Tiến trình AI thực thi tính toán BERTScore (P/R/F1), phân rã mệnh đề rubric coverage, hiệu chỉnh hồi quy Ridge và tạo nhận xét.
   - `AiScoringClient` nhận HTTP 200, parse kết quả thành `EvaluateResult`. Nếu AI lỗi hoặc mất kết nối, client ném ngay lỗi 502/503 (không dùng fallback rule) làm rollback toàn bộ transaction CSDL.
9. `InterviewService` gọi `saveAiEvaluation`:
   - Khởi tạo thực thể `EvaluationResult`, gán `predictedScore`, `bertscorePrecision`, `bertscoreRecall`, `bertscoreF1`, `coverageScore`, `strengths`, `missingPoints`, `feedback`.
   - Lưu vào CSDL qua `evaluationResultRepository.save(result)`.
10. Service kiểm tra nếu tất cả câu hỏi trong phiên đã có kết quả đánh giá: cập nhật `session.setStatus(SessionStatus.COMPLETED)`, gán `completedAt` và lưu lại phiên.
11. Service ánh xạ `EvaluationResult` thành `EvaluationResponse` và trả về cho Controller để hiển thị giao diện đánh giá chi tiết `EvalBlock` trên Frontend.

---

## 4. Các Design Pattern thực tế trong mã nguồn

Hệ thống mã nguồn Backend của module M4 áp dụng 7 mẫu thiết kế (Design Patterns) rõ ràng và chuẩn mực:

### 4.1. Repository Pattern
- **Lớp tham gia:** `InterviewSessionRepository` (`InterviewSessionRepository.java:8`), `InterviewSessionQuestionRepository` (`InterviewSessionQuestionRepository.java:11`), `EvaluationResultRepository` (`EvaluationResultRepository.java:8`), `EvaluationRubricRepository` (`EvaluationRubricRepository.java:8`).
- **Hiện thực:** Kế thừa `org.springframework.data.jpa.repository.JpaRepository`.
- **Dẫn chứng mã nguồn cụ thể:**
  - `InterviewSessionRepository.java:11-13`: Khai báo `@Lock(LockModeType.PESSIMISTIC_WRITE)` trên phương thức `findForUpdate(Integer id)` để thực thi truy vấn khóa dòng CSDL `SELECT ... FOR UPDATE`.
  - `InterviewSessionQuestionRepository.java:13-19`: Định nghĩa câu lệnh JPQL tùy biến `findBySessionIdOrdered` kết hợp `JOIN FETCH` để triệt tiêu bài toán N+1 query khi tải câu hỏi phiên.
- **Ưu điểm cho HireLens:** Tách biệt tuyệt đối logic nghiệp vụ tại tầng Service khỏi các câu lệnh SQL/JPQL cụ thể. Cơ chế khóa bi quan tích hợp sẵn trong Repository giúp hệ thống ngăn chặn triệt để hiện tượng xung đột dữ liệu và gian lận khi ứng viên nộp nhiều câu trả lời đồng thời từ các thiết bị/tab khác nhau.

### 4.2. Data Transfer Object (DTO) Pattern
- **Lớp tham gia:** `InterviewDtos.CreateSessionRequest` (`InterviewDtos.java:27`), `InterviewDtos.SessionResponse` (`InterviewDtos.java:39`), `InterviewDtos.SubmitResponseRequest` (`InterviewDtos.java:53`), `InterviewDtos.EvaluationResponse` (`InterviewDtos.java:59`), `AiScoringDtos.CriterionIn` (`AiScoringDtos.java:11`), `AiScoringDtos.EvaluateResult` (`AiScoringDtos.java:21`), `ServiceDtos.InterviewContext` (`ServiceDtos.java:8`).
- **Hiện thực:** Sử dụng cấu trúc Java `record` bất biến (immutable), tích hợp các annotation kiểm tra ràng buộc của Jakarta Bean Validation (`@NotNull`, `@NotBlank`, `@Size(max=4000)`).
- **Ưu điểm cho HireLens:** Che giấu hoàn toàn cấu trúc bảng CSDL nội bộ và các trường nhạy cảm khỏi phía Client; ngăn chặn rủi ro rò rỉ dữ liệu hoặc lỗi `LazyInitializationException` khi chuyển đổi đối tượng JPA sang JSON. Cho phép lọc và chặn các câu trả lời rỗng hoặc vượt quá 4.000 ký tự ngay tại tầng Controller trước khi tiêu tốn tài nguyên gọi mô hình AI.

### 4.3. Dependency Injection (DI) & Inversion of Control (IoC)
- **Lớp tham gia:** `InterviewController` (`InterviewController.java:13-16`), `InterviewService` (`InterviewService.java:22-33`), `AiScoringClient` (`AiScoringClient.java:25-29`), `ServiceHttpClient` (`ServiceHttpClient.java:17`).
- **Hiện thực:** Áp dụng Constructor Injection thông qua annotation Lombok `@RequiredArgsConstructor` kết hợp các stereotype `@Service`, `@RestController`, `@Component` của Spring Framework.
- **Ưu điểm cho HireLens:** Giảm thiểu tối đa mức độ phụ thuộc cứng giữa các thành phần. Tạo điều kiện thuận lợi để viết Unit Test và Integration Test độc lập: có thể dễ dàng mock `AiScoringClient` hoặc `ServiceHttpClient` để kiểm thử toàn diện logic của `InterviewService` mà không bắt buộc phải khởi chạy các tiến trình nặng như CSDL MySQL hay AI FastAPI.

### 4.4. Facade Pattern
- **Lớp tham gia:** `InterviewService` (`InterviewService.java:23-298`).
- **Hiện thực:** `InterviewService` đóng vai trò là một Facade thống nhất cho toàn bộ hệ thống con ôn tập và chấm phỏng vấn. Nó ẩn giấu sự phức tạp của 8 thành phần con:
  - Tích hợp mạng với `recruitment-service` qua `ServiceHttpClient` (`:48-51`).
  - Thuật toán đồ thị kỹ năng qua `QuestionSelectionService` (`:68`).
  - Khóa bi quan và kiểm tra phiên qua `InterviewSessionRepository` (`:108-112`).
  - Quản lý thứ tự câu hỏi qua `InterviewSessionQuestionRepository` (`:87-92`).
  - Quản lý câu trả lời qua `InterviewResponseRepository` (`:119-122`).
  - Truy vấn barem rubric qua `EvaluationRubricRepository` (`:165`).
  - Thích ứng mạng và gọi mô hình AI qua `AiScoringClient` (`:169-175`).
  - Quản lý transaction phân tán và lưu kết quả qua `EvaluationResultRepository` (`:179-208`).
- **Ưu điểm cho HireLens:** `InterviewController` được giữ cực kỳ tinh gọn (thin controller), chỉ tập trung vào việc định tuyến URL và validate DTO mà không cần biết chi tiết phức tạp về cách thức khóa hàng CSDL, cách tính điểm đồ thị hay cách gọi dịch vụ ngoài.

### 4.5. Adapter / Client Pattern
- **Lớp tham gia:** `AiScoringClient` (`AiScoringClient.java:26-118`) và `ServiceHttpClient` (`ServiceHttpClient.java:13-42`).
- **Hiện thực:**
  - `AiScoringClient`: Đóng vai trò Adapter chuyển đổi giữa dữ liệu thực thể Java (`EvaluationRubric`, `InterviewQuestion`, `InterviewResponse`) và đặc tả API của Python FastAPI (`POST /v1/interview/evaluate`). Lớp này thực hiện chuẩn hóa trọng số rubric sang kiểu `double` tổng bằng 1.0 để tương thích với kiểm tra Pydantic của Python, đồng thời chuyển đổi các mã lỗi mạng hoặc timeout thành `ApiException` trong Java.
  - `ServiceHttpClient`: Đóng vai trò generic client adapter cho các cuộc gọi Service-to-Service nội bộ, tự động đính kèm shared token `X-Service-Token` vào header để vượt qua bộ lọc `InternalAccessFilter`.
- **Ưu điểm cho HireLens:** Cách ly hoàn toàn mã nguồn Spring Boot khỏi các thay đổi về giao thức hoặc kiến trúc của dịch vụ AI FastAPI. Khi dịch vụ AI thay đổi định dạng phản hồi hoặc nâng cấp mô hình, lập trình viên chỉ cần chỉnh sửa duy nhất `AiScoringClient` mà không làm xáo trộn luồng nghiệp vụ của toàn hệ thống.

### 4.6. Singleton Pattern
- **Lớp tham gia:** `SkillGraph` (`source/recruit_system/backend/common/src/main/java/recruit/demo/kb/SkillGraph.java:19-36`).
- **Hiện thực:** Khởi tạo cá thể tĩnh duy nhất lúc nạp lớp:
  ```java
  private static final SkillGraph SHARED = load();
  public static SkillGraph shared() { return SHARED; }
  ```
  Lớp `QuestionSelectionService` sử dụng cá thể này qua `private final SkillGraph graph = SkillGraph.shared();` (`QuestionSelectionService.java:9`).
- **Ưu điểm cho HireLens:** Đồ thị tri thức kỹ năng (`SkillGraph`) là một cấu trúc dữ liệu đồ thị phức tạp được xây dựng từ tệp tài nguyên JSON, chứa hàng trăm nút kỹ năng và cạnh quan hệ liên kết công nghệ. Việc áp dụng Singleton giúp đồ thị chỉ được đọc và phân tích một lần duy nhất vào bộ nhớ RAM khi ứng dụng khởi động, tránh việc tải lại tệp tin gây lãng phí CPU và bộ nhớ trong mỗi lần tạo phiên phỏng vấn.

### 4.7. Builder Pattern
- **Lớp tham gia:** `InterviewSession` (`InterviewSession.java:15`), `InterviewSessionQuestion` (`InterviewSessionQuestion.java:14`), `InterviewResponse` (`InterviewResponse.java:15`), `EvaluationResult` (`EvaluationResult.java:19`).
- **Hiện thực:** Sử dụng annotation `@Builder` của Lombok trên các lớp thực thể JPA. Được gọi trực tiếp tại `InterviewService.java:73-82`, `InterviewService.java:87-92`, `InterviewService.java:120`, `InterviewService.java:190`.
- **Ưu điểm cho HireLens:** Cung cấp cú pháp khởi tạo đối tượng rõ ràng, có thể thiết lập linh hoạt các thuộc tính tùy chọn mà không làm phát sinh các constructor cồng kềnh với quá nhiều tham số cùng kiểu dữ liệu (như `candidateId`, `candidateUserId`, `jobId`, `applicationId`), loại bỏ nguy cơ truyền nhầm vị trí tham số.

---

## 5. Bảng truy vết phần tử và quan hệ (Traceability Matrix)

### 5.1. Bảng truy vết phần tử (Elements)

| STT | Tên phần tử (`key`) | Loại (`kind`) | Stereotype | Gói cha (`parent`) | Nguồn truy vết trong mã nguồn (`src`) |
|:---:|:---|:---|:---|:---|:---|
| 1 | `View` | package | — | — | `backend/interview-service/.../dto/InterviewDtos.java:11` |
| 2 | `Controller` | package | — | — | `backend/interview-service/.../controller/InterviewController.java:1` |
| 3 | `Model` | package | — | — | `backend/interview-service/.../service/InterviewService.java:1` |
| 4 | `CreateSessionRequest` | class | dto | `View` | `backend/interview-service/.../dto/InterviewDtos.java:27` |
| 5 | `SessionResponse` | class | dto | `View` | `backend/interview-service/.../dto/InterviewDtos.java:39` |
| 6 | `SubmitResponseRequest` | class | dto | `View` | `backend/interview-service/.../dto/InterviewDtos.java:53` |
| 7 | `EvaluationResponse` | class | dto | `View` | `backend/interview-service/.../dto/InterviewDtos.java:59` |
| 8 | `InterviewController` | class | control | `Controller` | `backend/interview-service/.../controller/InterviewController.java:14` |
| 9 | `InterviewService` | class | service | `Model` | `backend/interview-service/.../service/InterviewService.java:23` |
| 10 | `QuestionSelectionService` | class | service | `Model` | `backend/interview-service/.../service/QuestionSelectionService.java:8` |
| 11 | `AiScoringClient` | class | client | `Model` | `backend/interview-service/.../service/AiScoringClient.java:26` |
| 12 | `ServiceHttpClient` | class | client | `Model` | `backend/common/.../client/ServiceHttpClient.java:13` |
| 13 | `InterviewSessionRepository` | interface | repository | `Model` | `backend/interview-service/.../repository/InterviewSessionRepository.java:8` |
| 14 | `InterviewSessionQuestionRepository` | interface | repository | `Model` | `backend/interview-service/.../repository/InterviewSessionQuestionRepository.java:11` |
| 15 | `EvaluationResultRepository` | interface | repository | `Model` | `backend/interview-service/.../repository/EvaluationResultRepository.java:8` |
| 16 | `EvaluationRubricRepository` | interface | repository | `Model` | `backend/interview-service/.../repository/EvaluationRubricRepository.java:8` |
| 17 | `InterviewSession` | class | entity | `Model` | `backend/interview-service/.../entity/InterviewSession.java:16` |
| 18 | `InterviewSessionQuestion` | class | entity | `Model` | `backend/interview-service/.../entity/InterviewSessionQuestion.java:15` |
| 19 | `InterviewResponse` | class | entity | `Model` | `backend/interview-service/.../entity/InterviewResponse.java:16` |
| 20 | `EvaluationResult` | class | entity | `Model` | `backend/interview-service/.../entity/EvaluationResult.java:20` |
| 21 | `EvaluationRubric` | class | entity | `Model` | `backend/interview-service/.../entity/EvaluationRubric.java:20` |

### 5.2. Bảng truy vết quan hệ (Relations)

| STT | Từ phần tử (`from`) | Tới phần tử (`to`) | Loại quan hệ (`kind`) | Bội số (`Mult`) | Nhãn (`label`) | Nguồn truy vết (`src`) |
|:---:|:---|:---|:---|:---:|:---|:---|
| 1 | `InterviewController` | `CreateSessionRequest` | dependency | — | uses | `.../controller/InterviewController.java:24` |
| 2 | `InterviewController` | `SessionResponse` | dependency | — | returns | `.../controller/InterviewController.java:24` |
| 3 | `InterviewController` | `SubmitResponseRequest` | dependency | — | uses | `.../controller/InterviewController.java:41` |
| 4 | `InterviewController` | `EvaluationResponse` | dependency | — | returns | `.../controller/InterviewController.java:42` |
| 5 | `InterviewController` | `InterviewService` | association | 1 → 1 | interviewService | `.../controller/InterviewController.java:16` |
| 6 | `InterviewService` | `QuestionSelectionService` | association | 1 → 1 | questionSelection | `.../service/InterviewService.java:32` |
| 7 | `InterviewService` | `AiScoringClient` | association | 1 → 1 | aiScoringClient | `.../service/InterviewService.java:31` |
| 8 | `InterviewService` | `ServiceHttpClient` | association | 1 → 1 | serviceHttp | `.../service/InterviewService.java:33` |
| 9 | `InterviewService` | `InterviewSessionRepository` | association | 1 → 1 | sessionRepository | `.../service/InterviewService.java:27` |
| 10 | `InterviewService` | `InterviewSessionQuestionRepository` | association | 1 → 1 | sessionQuestionRepository | `.../service/InterviewService.java:28` |
| 11 | `InterviewService` | `EvaluationResultRepository` | association | 1 → 1 | evaluationResultRepository | `.../service/InterviewService.java:30` |
| 12 | `InterviewService` | `EvaluationRubricRepository` | association | 1 → 1 | rubricRepository | `.../service/InterviewService.java:26` |
| 13 | `InterviewSessionRepository` | `InterviewSession` | dependency | — | manages | `.../repository/InterviewSessionRepository.java:8` |
| 14 | `InterviewSessionQuestionRepository` | `InterviewSessionQuestion` | dependency | — | manages | `.../repository/InterviewSessionQuestionRepository.java:11` |
| 15 | `EvaluationResultRepository` | `EvaluationResult` | dependency | — | manages | `.../repository/EvaluationResultRepository.java:8` |
| 16 | `EvaluationRubricRepository` | `EvaluationRubric` | dependency | — | manages | `.../repository/EvaluationRubricRepository.java:8` |
| 17 | `InterviewSession` | `InterviewSessionQuestion` | composition | 1 → 1..* | questions | `.../entity/InterviewSessionQuestion.java:23` |
| 18 | `InterviewSessionQuestion` | `InterviewResponse` | association | 1 → 0..1 | response | `.../entity/InterviewResponse.java:24` |
| 19 | `InterviewResponse` | `EvaluationResult` | association | 1 → 0..1 | evaluation | `.../entity/EvaluationResult.java:28` |

---

## 6. Mâu thuẫn giữa tài liệu và mã nguồn (Discrepancies)

1. **Kiến trúc triển khai ứng dụng:**
   - *Báo cáo đồ án v6:* Mô tả toàn bộ nghiệp vụ phỏng vấn nằm chung trong một ứng dụng Spring Boot nguyên khối (Monolith) truy cập trực tiếp vào cùng một cơ sở dữ liệu MySQL với các module khác.
   - *Mã nguồn thực tế (commit `1c96706`):* Đã được phân rã thành **Microservices**: `interview-service` (cổng 8083) sở hữu CSDL riêng biệt `hirelens_interview`, không có foreign key vật lý sang các bảng của `recruitment-service` hay `identity-service`. Việc lấy ngữ cảnh phỏng vấn được thực hiện độc lập qua giao thức mạng HTTP REST bằng `ServiceHttpClient`.
   - *Quyết định thiết kế:* Biểu đồ được xây dựng hoàn toàn bám sát theo kiến trúc microservices thực tế trong mã nguồn theo quyết định của kiến trúc sư dự án.

2. **Cơ chế xử lý khi dịch vụ AI gặp sự cố (Fallback Mechanism):**
   - *Tài liệu sơ khởi:* Đề xuất có cơ chế rule-based dự phòng để tính điểm cơ bản khi AI ngoại tuyến.
   - *Mã nguồn thực tế (`AiScoringClient.java:46`, `application.yml:44`):* Thuộc tính `fallback-to-rule` được viết cứng là `false`. Khi dịch vụ AI FastAPI không khả dụng, client ném ngay lỗi `503 Service Unavailable` hoặc `502 Bad Gateway`. Toàn bộ transaction tại `InterviewService.submitAndEvaluate` được rollback hoàn toàn, không lưu câu trả lời hay điểm số giả lập vào CSDL.
   - *Quyết định thiết kế:* Giữ nguyên logic chặt chẽ của mã nguồn để phản ánh đúng tính toàn vẹn dữ liệu trong hệ thống.

---

## 7. Điểm cần xác nhận (Open Questions)

1. **Cơ chế xác thực ngữ cảnh người dùng kép (User Context Propagation):**
   - Hiện tại, khi `interview-service` gọi `recruitment-service` qua `/internal/interview-context?userId={id}`, hệ thống chỉ sử dụng khóa bí mật chia sẻ `X-Service-Token` ở cấp độ service mà không đính kèm JWT của người dùng (Token Relay). Điều này đồng nghĩa `recruitment-service` hoàn toàn tin cậy tham số `userId` do `interview-service` cung cấp. Cần xác nhận xem trong tương lai có cần bổ sung việc chuyển tiếp JWT người dùng để tăng cường kiểm soát truy cập phân tán hay không.
2. **Kế hoạch mở rộng ngân hàng câu hỏi cấp độ Senior:**
   - Ngân hàng câu hỏi v2 trong cơ sở dữ liệu hiện tại chỉ bao gồm 30 câu hỏi chuẩn hóa thuộc 3 cấp độ: `Intern`, `Junior`, `Middle`. Đối với các tin tuyển dụng cấp độ `Senior` hoặc `Lead`, thuật toán `QuestionSelectionService.level()` hiện tại đang tự động ánh xạ mục tiêu về cấp độ `Middle`. Cần xác nhận lộ trình bổ sung các bộ câu hỏi và barem rubric chuẩn hóa dành riêng cho cấp độ Senior trong các phiên bản cập nhật tiếp theo.
