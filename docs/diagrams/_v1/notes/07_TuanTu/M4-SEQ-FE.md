# Ghi chú thiết kế - Biểu đồ tuần tự M4-SEQ-FE

## 1. Thông tin chung

- **Mã biểu đồ:** `M4-SEQ-FE`
- **Loại biểu đồ:** Sequence Diagram (Biểu đồ tuần tự)
- **Tên biểu đồ:** Biểu đồ tuần tự chi tiết - Ôn tập và chấm phỏng vấn (Frontend)
- **Module:** M4 - Ôn tập và chấm phỏng vấn (tương ứng Module 3 trong tài liệu `source/recruit_system/docs/Module3_Interview_Flow.md`)
- **Phạm vi kiến trúc:** Phía Frontend React (SPA).
- **Ràng buộc nhất quán:**
  - Lifelines và operations khớp 1-1 với biểu đồ lớp chi tiết [M4-CLS-FE.json](file:///home/hocnguyen/Documents/VPProjects/diagrams/specs/06_LopChiTiet/M4-CLS-FE.json).
  - Tương ứng với các bước 8 đến 17 trong kịch bản kịch bản hoạt động [M4-ACT.md](file:///home/hocnguyen/Documents/VPProjects/diagrams/notes/02_HoatDong/M4-ACT.md) và biểu đồ hoạt động [M4-ACT.json](file:///home/hocnguyen/Documents/VPProjects/diagrams/specs/02_HoatDong/M4-ACT.json).

---

## 2. Kịch bản văn bản đánh số (Scenario khớp 1-1 với `seq`)

Kịch bản thể hiện quá trình ứng viên gửi câu trả lời cho một câu hỏi phỏng vấn và nhận kết quả chấm điểm trực quan từ AI:

1. **seq 1 (`user -> page: submit()`):** Người dùng (Ứng viên) nhấn nút **"Gửi & nhận đánh giá"** trên giao diện [CandidateInterviewPage.tsx](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx#L40) để nộp nội dung câu trả lời.
2. **seq 2 (`page -> toastCtx: toast("Hãy nhập câu trả lời")`):** *[Alt validateAnswer - guard: câu trả lời trống]* Trang kiểm tra `!answer.trim()`. Nếu câu trả lời trống, trang gọi `toastCtx.toast()` để cảnh báo ứng viên cần nhập câu trả lời.
3. **seq 3 (`toastCtx -> page: return void`):** Hook `toastCtx` hiển thị toast thông báo cảnh báo và kết thúc xử lý.
4. **seq 4 (`page -> user: return void`):** Trang hoàn tất xử lý ngoại lệ câu trả lời trống, giữ nguyên giao diện để người dùng tiếp tục nhập.
5. **seq 5 (`page -> api: submit(sessionId, questionId, answerText)`):** *[Alt validateAnswer - guard: câu trả lời hợp lệ]* Nếu câu trả lời hợp lệ, trang kích hoạt trạng thái bận `busy = true`, lưu câu trả lời vào `lastAnswer` và gọi `interviewsApi.submit()` với `sessionId`, `questionId`, `answerText`.
6. **seq 6 (`api -> client: api<T>(path, options)`):** [interviewsApi](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/api/client.ts#L141) gọi hàm HTTP client cốt lõi `api<T>()` với đường dẫn `/interviews/sessions/{sessionId}/responses` và payload JSON.
7. **seq 7 (`client -> server: POST /api/interviews/sessions/{id}/responses`):** Lớp `client` đính kèm JWT Authorization header và thực hiện HTTP request POST gửi sang [InterviewController](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/backend/interview-service/src/main/java/recruit/demo/controller/InterviewController.java#L40) của backend.
8. **seq 8 (`server -> client: return 409/500 Error`):** *[Alt submitCall - guard: lỗi máy chủ hoặc AI]* Máy chủ phản hồi mã lỗi HTTP (ví dụ: HTTP 409 Conflict do phiên đã hoàn thành, hoặc HTTP 502/503 do dịch vụ AI chấm điểm gặp sự cố/timeout).
9. **seq 9 (`client -> api: return ApiError`):** Client trích xuất thông báo lỗi từ response và ném đối tượng `ApiError`.
10. **seq 10 (`api -> page: return Error`):** Ngoại lệ được chuyển tiếp về hàm `submit()` trong trang [CandidateInterviewPage.tsx](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx#L47).
11. **seq 11 (`page -> toastCtx: toast("Đánh giá thất bại")`):** Khối `catch` của trang bắt lỗi và gọi `toastCtx.toast()` thông báo lỗi "Đánh giá thất bại" cho ứng viên.
12. **seq 12 (`toastCtx -> page: return void`):** Toast context hoàn tất hiển thị thông báo lỗi.
13. **seq 13 (`server -> client: return 200 EvaluationResponse`):** *[Alt submitCall - guard: chấm điểm thành công]* Máy chủ hoàn tất chấm điểm thành công và trả về mã HTTP 200 kèm body `EvaluationResponse`.
14. **seq 14 (`client -> api: return EvaluationDto`):** Client giải mã JSON thành đối tượng `EvaluationDto`.
15. **seq 15 (`api -> page: return EvaluationDto`):** `interviewsApi` trả kết quả `EvaluationDto` về cho trang `CandidateInterviewPage`. Trang cập nhật state `evaluation`.
16. **seq 16 (`page -> api: getSession(id)`):** Trang gọi `interviewsApi.getSession(session.id)` để làm mới dữ liệu phiên phỏng vấn (cập nhật trạng thái `currentIndex` và tiến độ).
17. **seq 17 (`api -> page: return SessionDto`):** `interviewsApi` trả về đối tượng `SessionDto` cập nhật.
18. **seq 18 (`page -> api: summary(id)`):** Trang gọi `interviewsApi.summary(session.id)` để lấy báo cáo tổng kết phiên cập nhật.
19. **seq 19 (`api -> page: return SessionSummaryDto`):** `interviewsApi` trả về đối tượng `SessionSummaryDto`.
20. **seq 20 (`page -> toastCtx: toast("Đã lưu kết quả đánh giá")`):** Trang gọi `toastCtx.toast()` thông báo cho người dùng kết quả đánh giá đã được lưu thành công.
21. **seq 21 (`toastCtx -> page: return void`):** Toast hiển thị hoàn tất.
22. **seq 22 (`page -> evalBlock: render()`):** Trang kích hoạt render component [EvalBlock](file:///home/hocnguyen/Documents/VPProjects/source/recruit_system/frontend/src/components/common/EvalBlock.tsx#L24) với đối tượng dữ liệu `evaluation`.
23. **seq 23 (`evalBlock -> page: return JSX.Element`):** `EvalBlock` trả về khối giao diện gồm vòng tròn điểm số, chỉ số BERTScore, độ phủ tiêu chí barem và nhận xét phản hồi.
24. **seq 24 (`page -> user: return void`):** Trang hoàn thành luồng xử lý, đặt lại `busy = false`, hiển thị kết quả đánh giá trực quan và kích hoạt nút "Câu tiếp theo" cho người dùng.

---

## 3. Bảng truy vết thông điệp (Traceability Matrix)

| Seq | Nguồn phát (`from`) | Đích nhận (`to`) | Thao tác (`operation`) | Tham số / Kiểu trả về (`params`) | Loại (`kind`) | Rẽ nhánh (`fragment`) | Nguồn truy vết (`src`) |
|:---:|:---|:---|:---|:---|:---|:---|:---|
| 1 | `user` | `page` | `submit` | `[]` | sync | — | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:40` |
| 2 | `page` | `toastCtx` | `toast` | `["msg"]` | sync | `validateAnswer: câu trả lời trống` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:41` |
| 3 | `toastCtx` | `page` | `toast` | `"void"` | return | `validateAnswer: câu trả lời trống` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:41` |
| 4 | `page` | `user` | `submit` | `"void"` | return | `validateAnswer: câu trả lời trống` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:41` |
| 5 | `page` | `api` | `submit` | `["sessionId", "questionId", "answerText"]` | sync | `validateAnswer: câu trả lời hợp lệ` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:44` |
| 6 | `api` | `client` | `api<T>` | `["path", "options"]` | sync | `validateAnswer: câu trả lời hợp lệ` | `source/recruit_system/frontend/src/api/client.ts:141` |
| 7 | `client` | `server` | `POST /api/interviews/sessions/{id}/responses` | `["questionId", "answerText"]` | sync | `validateAnswer: câu trả lời hợp lệ` | `source/recruit_system/frontend/src/api/client.ts:43` |
| 8 | `server` | `client` | `POST /api/interviews/sessions/{id}/responses` | `"409/500 Error"` | return | `submitCall: lỗi máy chủ hoặc AI` | `source/recruit_system/frontend/src/api/client.ts:44` |
| 9 | `client` | `api` | `api<T>` | `"ApiError"` | return | `submitCall: lỗi máy chủ hoặc AI` | `source/recruit_system/frontend/src/api/client.ts:45` |
| 10 | `api` | `page` | `submit` | `"Error"` | return | `submitCall: lỗi máy chủ hoặc AI` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:47` |
| 11 | `page` | `toastCtx` | `toast` | `["msg"]` | sync | `submitCall: lỗi máy chủ hoặc AI` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:47` |
| 12 | `toastCtx` | `page` | `toast` | `"void"` | return | `submitCall: lỗi máy chủ hoặc AI` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:47` |
| 13 | `server` | `client` | `POST /api/interviews/sessions/{id}/responses` | `"200 EvaluationResponse"` | return | `submitCall: chấm điểm thành công` | `source/recruit_system/frontend/src/api/client.ts:48` |
| 14 | `client` | `api` | `api<T>` | `"EvaluationDto"` | return | `submitCall: chấm điểm thành công` | `source/recruit_system/frontend/src/api/client.ts:48` |
| 15 | `api` | `page` | `submit` | `"EvaluationDto"` | return | `submitCall: chấm điểm thành công` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:44` |
| 16 | `page` | `api` | `getSession` | `["id"]` | sync | `submitCall: chấm điểm thành công` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:45` |
| 17 | `api` | `page` | `getSession` | `"SessionDto"` | return | `submitCall: chấm điểm thành công` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:45` |
| 18 | `page` | `api` | `summary` | `["id"]` | sync | `submitCall: chấm điểm thành công` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:45` |
| 19 | `api` | `page` | `summary` | `"SessionSummaryDto"` | return | `submitCall: chấm điểm thành công` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:45` |
| 20 | `page` | `toastCtx` | `toast` | `["msg"]` | sync | `submitCall: chấm điểm thành công` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:46` |
| 21 | `toastCtx` | `page` | `toast` | `"void"` | return | `submitCall: chấm điểm thành công` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:46` |
| 22 | `page` | `evalBlock` | `render` | `[]` | sync | `submitCall: chấm điểm thành công` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:81` |
| 23 | `evalBlock` | `page` | `render` | `"JSX.Element"` | return | `submitCall: chấm điểm thành công` | `source/recruit_system/frontend/src/components/common/EvalBlock.tsx:115` |
| 24 | `page` | `user` | `submit` | `"void"` | return | `submitCall: chấm điểm thành công` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:48` |

---

## 4. Ghi chú đối chiếu so với biểu đồ hoạt động (M4-ACT)

1. **Phạm vi hiển thị:** Biểu đồ hoạt động `M4-ACT` mô tả xuyên suốt 5 làn (Người dùng, Frontend, recruitment-service, interview-service, interview-ai) từ khâu tạo phiên đến khi hoàn thành toàn bộ phiên. Biểu đồ tuần tự `M4-SEQ-FE` tập trung đặc tả chi tiết nội bộ bên Frontend React cho thao tác nộp bài và nhận đánh giá (`submit()`), tương ứng từ bước 8 đến bước 17 trong kịch bản chính của M4-ACT, kèm theo 2 ngoại lệ chính (Ngoại lệ 2: câu trả lời trống, và Ngoại lệ 3/4: máy chủ từ chối / AI lỗi).
2. **Cập nhật đồng thời phiên và tổng kết:** Sau khi submit thành công, mã nguồn React thực thi `Promise.all([interviewsApi.getSession(session.id), interviewsApi.summary(session.id)])` và gọi `interviewsApi.mine()`. Trên biểu đồ tuần tự để đảm bảo giới hạn số lượng message (≤ 26 message) và trực quan hóa thứ tự, luồng tuần tự thể hiện các lệnh gọi cốt lõi `getSession` và `summary`, cùng bước render `EvalBlock` trực quan hóa kết quả.
