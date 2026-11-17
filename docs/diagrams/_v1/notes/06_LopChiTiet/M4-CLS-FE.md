# Ghi chú thiết kế - Biểu đồ lớp chi tiết M4-CLS-FE

## 1. Thông tin chung
- **Mã biểu đồ:** `M4-CLS-FE`
- **Tên biểu đồ:** Biểu đồ lớp chi tiết - Ôn tập và chấm phỏng vấn (Frontend)
- **Module:** M4 - Ôn tập và chấm phỏng vấn
- **Phạm vi nguồn:** `source/recruit_system/frontend/src/` (trang ứng viên `CandidateInterviewPage`, các component dùng chung `EvalBlock`, `ScoreRing`, `EvalRow`, `ChatBubble`, context `ToastContext`, API client `interviewsApi`, `apiClient`, và các interfaces/DTOs định kiểu dữ liệu).
- **Căn cứ thiết kế:** Tuân thủ quy tắc mô hình hóa MVC cho React TypeScript (DIAGRAM_RULES.md §1.2 & §5.2), bám sát biểu đồ hoạt động `M4-ACT` (`diagrams/specs/02_HoatDong/M4-ACT.json` và `diagrams/notes/02_HoatDong/M4-ACT.md`).

---

## 2. Diễn giải vai trò từng lớp và luồng gọi chính

### 2.1. Phân tầng kiến trúc MVC trên Frontend

#### Tầng View (Stereotype `«boundary»`):
1. **`CandidateInterviewPage`** (`source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:9`):
   - Màn hình chính của phân hệ luyện phỏng vấn phía ứng viên.
   - Quản lý trạng thái vòng đời phiên luyện tập: `session` (phiên hiện tại), `history` (danh sách phiên trước đây), `summary` (báo cáo tổng kết), `idx` (chỉ số câu hỏi hiện tại), `answer` (nội dung câu trả lời đang soạn), `evaluation` (kết quả chấm điểm câu hiện tại), và cờ trạng thái xử lý `busy`.
   - Cung cấp các hàm xử lý sự kiện: `start()` (tạo phiên mới 6 câu), `openSession(id)` (mở lại phiên đang dang dở/đã làm), `submit()` (gửi câu trả lời để chấm điểm AI), `next()` (chuyển sang câu tiếp theo).
2. **`EvalBlock`** (`source/recruit_system/frontend/src/components/common/EvalBlock.tsx:24`):
   - Component hiển thị trực quan toàn bộ kết quả chấm điểm của câu trả lời.
   - Nhận props `evaluation: InterviewEvaluation`. Hiển thị vòng tròn điểm trực quan, các chỉ số BERTScore (Precision, Recall, F1), độ phủ tiêu chí `coverageScore`, chi tiết từng barem rubric `criterionResults`, và nhận xét phản hồi `comment`.
3. **`ScoreRing`** (`source/recruit_system/frontend/src/components/common/ScoreRing.tsx:14`):
   - Component hiển thị vòng tròn điểm với conic gradient tương ứng với % điểm số (0–100).
4. **`EvalRow`** (`source/recruit_system/frontend/src/components/common/EvalBlock.tsx:11`):
   - Component hiển thị từng dòng chỉ số đánh giá (nhãn `label` và giá trị `value`).
5. **`ChatBubble`** (`source/recruit_system/frontend/src/components/common/ChatBubble.tsx:19`):
   - Bong bóng hội thoại hiển thị nội dung câu hỏi phỏng vấn từ AI (`role="ai"`) hoặc câu trả lời vừa gửi của ứng viên (`role="user"`).

#### Tầng Controller (Stereotype `«control»`):
6. **`ToastContext`** (`source/recruit_system/frontend/src/context/ToastContext.tsx:15`):
   - Cung cấp hook `useToast()` quản lý việc hiển thị thông báo phản hồi (thành công hoặc cảnh báo lỗi) tới người dùng.
7. **`interviewsApi`** (`source/recruit_system/frontend/src/api/client.ts:125`):
   - Module API client đóng vai trò controller giao tiếp với backend `interview-service`:
     - `createSession(body)`: gửi request `POST /interviews/sessions` để khởi tạo phiên phỏng vấn 6 câu.
     - `getSession(id)`: gửi request `GET /interviews/sessions/{id}` để lấy chi tiết phiên.
     - `submit(sessionId, questionId, answerText)`: gửi request `POST /interviews/sessions/{id}/responses` để gửi câu trả lời và nhận kết quả chấm điểm tức thì.
     - `summary(id)`: gửi request `GET /interviews/sessions/{id}/summary` để lấy báo cáo tổng kết phiên.
     - `mine()`: gửi request `GET /interviews/sessions/mine` để lấy danh sách các phiên gần đây của ứng viên.
     - `questions()`: gửi request `GET /interviews/questions` để tra cứu danh sách câu hỏi.

#### Tầng Model (Stereotype `«client»` & `«entity»`):
8. **`apiClient`** (`source/recruit_system/frontend/src/api/client.ts:32`):
   - Lớp client HTTP cơ sở (`api<T>`), tự động đính kèm `Bearer JWT token` từ `localStorage`, serialize dữ liệu JSON, xử lý mã phản hồi HTTP và trích xuất lỗi mạng.
9. **`ApiError`** (`source/recruit_system/frontend/src/api/client.ts:14`):
   - Lớp ngoại lệ mô hình hóa lỗi HTTP (chứa `status: number` và `message: string`).
10. **`SessionDto`** (`source/recruit_system/frontend/src/api/client.ts:261`):
    - Entity truyền tải dữ liệu phiên phỏng vấn: mã phiên, trạng thái (`CREATED`, `IN_PROGRESS`, `COMPLETED`), câu hiện tại `currentIndex`, tiêu đề việc làm `jobTitle`, và danh sách câu hỏi `questions`.
11. **`SessionQuestionItem`** (`source/recruit_system/frontend/src/api/client.ts:267`):
    - Cấu trúc từng câu hỏi nằm trong phiên: `questionId`, `sortOrder`, `topic`, `difficulty`, `questionText`.
12. **`EvaluationDto`** (`source/recruit_system/frontend/src/api/client.ts:285`):
    - Entity truyền tải kết quả chấm điểm từ backend/AI: điểm dự đoán `predictedScore`, chỉ số BERTScore (`bertscorePrecision`, `bertscoreRecall`, `bertscoreF1`), độ phủ barem `coverageScore`, điểm mạnh `coveredPoints`, điểm thiếu `missingPoints`, nhận xét `comment`, và danh sách barem chi tiết `criterionResults`.
13. **`CriterionResultDto`** (`source/recruit_system/frontend/src/api/client.ts:277`):
    - Kết quả đánh giá chi tiết cho từng tiêu chí barem rubric: `key`, `label`, `status`, `points`, `max_points`, `semantic_f1`, `feedback`.
14. **`SessionSummaryDto`** (`source/recruit_system/frontend/src/api/client.ts:281`):
    - Entity tổng kết phiên phỏng vấn: số câu đã chấm `answeredQuestions`, tổng số câu `totalQuestions`, điểm trung bình toàn phiên `averageScore`, và danh sách đánh giá từng câu `evaluations`.
15. **`InterviewEvaluation`** (`source/recruit_system/frontend/src/types/index.ts:101`):
    - Domain model dùng riêng cho tầng View (`EvalBlock`), được ánh xạ và chuẩn hóa kiểu dữ liệu từ `EvaluationDto`.

---

### 2.2. Luồng gọi chính (Trực tiếp từ M4-ACT)

1. **Khởi tạo phiên mới (`start`):**
   - Người dùng click nút "Bắt đầu phiên 6 câu" trên `CandidateInterviewPage`.
   - `CandidateInterviewPage.start()` gọi `interviewsApi.createSession({ jobId, questionCount: 6 })`.
   - `interviewsApi` ủy nhiệm cho `apiClient.api<SessionDto>()` gửi `POST /interviews/sessions`.
   - Sau khi nhận `SessionDto`, trang cập nhật state `session`, `idx = s.currentIndex`, làm trống khung soạn thảo `answer` và cập nhật danh sách `history` thông qua `interviewsApi.mine()`.
   - Hiển thị nội dung câu hỏi đầu tiên bằng `ChatBubble` (`role="ai"`).
2. **Nộp bài và chấm điểm (`submit`):**
   - Ứng viên nhập câu trả lời vào `answer` và bấm "Gửi & nhận đánh giá".
   - Kiểm tra `answer.trim()`: nếu rỗng, gọi `ToastContext.toast("Hãy nhập câu trả lời")` và ngưng xử lý.
   - Nếu hợp lệ, gọi `interviewsApi.submit(session.id, q.questionId, answer.trim())`.
   - Sau khi nhận `EvaluationDto`, trang chuyển đổi sang `InterviewEvaluation` và truyền vào `EvalBlock` để render kết quả chấm điểm (vòng tròn điểm qua `ScoreRing`, các dòng chỉ số qua `EvalRow`, nhận xét và barem).
   - Đồng thời, gọi song song `interviewsApi.getSession()` và `interviewsApi.summary()` để cập nhật tiến độ phiên và hiển thị bảng tổng kết.
3. **Chuyển câu tiếp theo (`next`):**
   - Ứng viên bấm "Câu tiếp theo", `CandidateInterviewPage.next()` cập nhật `idx = session.currentIndex`, xóa câu trả lời cũ và ẩn kết quả chấm điểm câu trước để sẵn sàng nhận câu hỏi tiếp theo.

---

## 3. Các mẫu thiết kế (Design Patterns) thực sự có trong code

Dự án Frontend HireLens áp dụng các mẫu thiết kế rõ ràng và chuẩn mực trong hệ sinh thái React TypeScript:

### 3.1. Context & Provider Pattern (kết hợp Dependency Injection)
- **Lớp / Module tham gia:**
  - `ToastProvider`, `ToastContext`, `useToast` (`source/recruit_system/frontend/src/context/ToastContext.tsx:15-40`).
  - `CandidateInterviewPage` (`source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:10`).
- **Vai trò:**
  - `ToastContext` định nghĩa interface giá trị thông báo và quản lý state cục bộ.
  - `ToastProvider` cung cấp giá trị thông qua React Context API.
  - `CandidateInterviewPage` sử dụng hook `useToast()` để tiêm (inject) hành vi hiển thị toast thông báo mà không cần nhận props từ component cha (tránh prop drilling).
- **Ưu điểm cụ thể cho HireLens:**
  - Giúp việc thông báo các sự kiện quan trọng trong quá trình phỏng vấn (tạo phiên lỗi, câu trả lời trống, chấm điểm thành công hoặc lỗi server) được tập trung hóa, nhất quán giao diện và dễ dàng sử dụng ở bất kỳ màn hình nào.

### 3.2. Facade Pattern (API Module)
- **Lớp / Module tham gia:**
  - `interviewsApi` (`source/recruit_system/frontend/src/api/client.ts:125-145`).
  - `apiClient` (`source/recruit_system/frontend/src/api/client.ts:32-49`).
- **Vai trò:**
  - `interviewsApi` đóng vai trò là một Facade, che giấu sự phức tạp của các HTTP requests bên dưới (endpoints URL, phương thức GET/POST, serialization `JSON.stringify`, header xác thực).
  - Cung cấp giao diện hàm mức cao trực quan: `createSession`, `getSession`, `submit`, `summary`, `mine`.
- **Ưu điểm cụ thể cho HireLens:**
  - Giúp mã nguồn tại `CandidateInterviewPage` hoàn toàn tách biệt khỏi các chi tiết giao thức mạng; khi backend microservices điều chỉnh URL endpoint hoặc cấu trúc payload, lập trình viên chỉ cần cập nhật tại một nơi duy nhất (`interviewsApi`).

### 3.3. DTO (Data Transfer Object) Pattern
- **Lớp / Module tham gia:**
  - `SessionDto`, `SessionQuestionItem`, `EvaluationDto`, `CriterionResultDto`, `SessionSummaryDto` (`source/recruit_system/frontend/src/api/client.ts:261-301`).
- **Vai trò:**
  - Đóng gói dữ liệu trao đổi giữa API Gateway / microservices và Frontend Client thành các TypeScript interface có định kiểu chặt chẽ (strict typing).
- **Ưu điểm cụ thể cho HireLens:**
  - Ngăn ngừa sai sót runtime khi truy xuất dữ liệu phản hồi chấm điểm phức tạp từ AI (các chỉ số BERTScore, danh sách bằng chứng đạt/thiếu, chi tiết từng barem rubric). Đảm bảo hợp đồng dữ liệu giữa `interview-service` và giao diện người dùng.

### 3.4. Composite View / Compound Component Pattern
- **Lớp / Module tham gia:**
  - `CandidateInterviewPage` lồng ghép `EvalBlock`, `ChatBubble` (`source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:70-85`).
  - `EvalBlock` lồng ghép `ScoreRing`, `EvalRow` (`source/recruit_system/frontend/src/components/common/EvalBlock.tsx:24-60`).
- **Vai trò:**
  - Tách nhỏ giao diện kết quả đánh giá phỏng vấn thành các thành phần trực quan chuyên biệt, có khả năng tái sử dụng độc lập (ví dụ `ScoreRing` tái sử dụng trong cả trang Matching M3 và Interview M4).
- **Ưu điểm cụ thể cho HireLens:**
  - Giao diện kết quả phỏng vấn AI có nhiều thông tin chi tiết (điểm tổng, điểm tương đồng, nhận xét, bằng chứng từng tiêu chí). Việc chia nhỏ component giúp quản lý bố cục rõ ràng, nâng cao hiệu năng re-render và trải nghiệm ôn luyện của ứng viên mượt mà.

---

## 4. Bảng truy vết phần tử (Traceability Matrix)

| STT | Tên phần tử | Loại (`kind`) | Stereotype | Gói cha (`parent`) | Nguồn trong mã nguồn (`src`) |
|:---:|:---|:---|:---|:---|:---|
| 1 | `pkg_view` | package | — | — | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx` |
| 2 | `CandidateInterviewPage` | class | boundary | `pkg_view` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:9` |
| 3 | `EvalBlock` | class | boundary | `pkg_view` | `source/recruit_system/frontend/src/components/common/EvalBlock.tsx:24` |
| 4 | `ScoreRing` | class | boundary | `pkg_view` | `source/recruit_system/frontend/src/components/common/ScoreRing.tsx:14` |
| 5 | `EvalRow` | class | boundary | `pkg_view` | `source/recruit_system/frontend/src/components/common/EvalBlock.tsx:11` |
| 6 | `ChatBubble` | class | boundary | `pkg_view` | `source/recruit_system/frontend/src/components/common/ChatBubble.tsx:19` |
| 7 | `pkg_controller` | package | — | — | `source/recruit_system/frontend/src/context/` |
| 8 | `ToastContext` | class | control | `pkg_controller` | `source/recruit_system/frontend/src/context/ToastContext.tsx:15` |
| 9 | `interviewsApi` | class | control | `pkg_controller` | `source/recruit_system/frontend/src/api/client.ts:125` |
| 10 | `pkg_model` | package | — | — | `source/recruit_system/frontend/src/api/client.ts` |
| 11 | `apiClient` | class | client | `pkg_model` | `source/recruit_system/frontend/src/api/client.ts:32` |
| 12 | `ApiError` | class | entity | `pkg_model` | `source/recruit_system/frontend/src/api/client.ts:14` |
| 13 | `SessionDto` | class | entity | `pkg_model` | `source/recruit_system/frontend/src/api/client.ts:261` |
| 14 | `SessionQuestionItem` | class | entity | `pkg_model` | `source/recruit_system/frontend/src/api/client.ts:267` |
| 15 | `SessionSummaryDto` | class | entity | `pkg_model` | `source/recruit_system/frontend/src/api/client.ts:281` |
| 16 | `EvaluationDto` | class | entity | `pkg_model` | `source/recruit_system/frontend/src/api/client.ts:285` |
| 17 | `CriterionResultDto` | class | entity | `pkg_model` | `source/recruit_system/frontend/src/api/client.ts:277` |
| 18 | `InterviewEvaluation` | class | entity | `pkg_model` | `source/recruit_system/frontend/src/types/index.ts:101` |

Tổng cộng: **18 phần tử** (gồm 3 packages và 15 lớp/entities/components), đảm bảo giới hạn ≤ 18 lớp theo yêu cầu.

---

## 5. Mâu thuẫn giữa tài liệu và source code

- **Kiến trúc phân hệ:**
  - Tài liệu báo cáo v6 mô tả backend nguyên khối monolith và chưa có phân hệ luyện phỏng vấn trực tiếp bằng BERTScore kết hợp rubric chấm theo microservice.
  - Source code thực tế tại commit `1c96706` triển khai phân hệ luyện phỏng vấn dưới dạng microservice riêng biệt (`interview-service` và `interview-ai`), với giao diện người dùng tương tác dạng hội thoại (`CandidateInterviewPage`), hỗ trợ phản hồi chi tiết đa tiêu chí (BERTScore P/R/F1, Ridge regression score, độ phủ rubric coverage). Toàn bộ biểu đồ lớp đã được chốt và thiết kế hoàn toàn theo mã nguồn thực tế.
