# Ghi chú thiết kế - Biểu đồ hoạt động M4-ACT

## 1. Thông tin chung

- **Mã biểu đồ:** `M4-ACT`
- **Loại biểu đồ:** Activity Diagram (Biểu đồ hoạt động)
- **Tên biểu đồ:** Biểu đồ hoạt động - Ôn tập phỏng vấn theo tin/CV và chấm một câu trả lời
- **Module:** M4 (Module 3 trong tài liệu repo: Luyện phỏng vấn và chấm điểm v2)
- **Phạm vi kiến trúc:** Microservices
  - **Người dùng:** Ứng viên (vai trò `CANDIDATE`) tương tác qua giao diện web.
  - **Frontend:** Ứng dụng React SPA (`frontend/src/pages/candidate/CandidateInterviewPage.tsx`, `EvalBlock.tsx`, `ChatBubble.tsx`, `api/client.ts`).
  - **recruitment-service:** Cung cấp ngữ cảnh phỏng vấn qua API nội bộ (`GET /internal/interview-context`) bao gồm kỹ năng JD bắt buộc, kỹ năng CV của ứng viên và cấp độ thâm niên.
  - **interview-service:** Điều phối toàn bộ vòng đời phiên ôn tập (`InterviewController`, `InterviewService`), thuật toán chọn câu hỏi theo ngữ cảnh (`QuestionSelectionService`), truy xuất tiêu chí barem rubric và gọi chấm điểm AI (`AiScoringClient`).
  - **interview-ai:** Dịch vụ AI chuyên biệt FastAPI (`AI/src/api.py`, `scoring.py`, `rubric.py`, `coverage.py`) chấm điểm dựa trên BERTScore, phân tích mệnh đề rubric và hiệu chỉnh hồi quy Ridge.

---

## 2. Kịch bản văn bản đánh số (Scenario)

### 2.1. Kịch bản chính (Main Success Flow)

1. **Ứng viên yêu cầu bắt đầu phiên:** Tại trang luyện phỏng vấn (`/candidate/interview`), ứng viên nhấn nút **"Bắt đầu phiên 6 câu"** (hoặc **"Tạo phiên mới"**) `[init]` → `[act_click_start]`.
2. **Frontend gửi yêu cầu tạo phiên:** Frontend gọi hàm `interviewsApi.createSession({ jobId, questionCount: 6 })` gửi request `POST /api/interviews/sessions` tới API Gateway, sau đó gateway chuyển tiếp tới `interview-service` `[act_send_create_session]`.
3. **interview-service truy vấn ngữ cảnh:** `interview-service` kiểm tra quyền `CANDIDATE`, sau đó gọi sang `recruitment-service` qua route nội bộ `GET /internal/interview-context?userId={id}&jobId={jobId}` `[act_get_context]`.
4. **recruitment-service kiểm tra hồ sơ và trích xuất ngữ cảnh:** `InternalRecruitmentController` kiểm tra trạng thái hoạt động của tài khoản ứng viên, truy vấn hồ sơ `candidate_profiles` `[dec_context_valid: hồ sơ hợp lệ]`. Service trích xuất danh sách kỹ năng bắt buộc từ tin tuyển dụng (`job_skills`), kỹ năng của ứng viên từ dữ liệu CV (`cv_data`), và xác định cấp độ mục tiêu (Intern / Junior / Middle).
5. **Chọn câu hỏi phỏng vấn tất định:** `QuestionSelectionService.select` lọc các câu hỏi đang kích hoạt (`is_active = 1`, `source = 'synthetic-ai-v2'`), tính điểm ưu tiên dựa trên:
   - Khớp kỹ năng JD bắt buộc (+40 điểm) hoặc kỹ năng CV (+20 điểm).
   - Khoảng cách trên đồ thị tri thức kỹ năng `SkillGraph` (+8 đến +16 điểm).
   - Phạt chênh lệch cấp độ thâm niên (-3 điểm mỗi bậc chênh lệch).
   - Phạt lặp lại câu hỏi đã xuất hiện trong 36 lượt gần nhất (-12 điểm).
   - Giới hạn đa dạng: tối đa 2 câu/chủ đề và khống chế số lượng câu theo từng dạng câu hỏi (Knowledge, Application, Scenario). Kết quả chọn ra 6 câu hỏi tối ưu `[act_select_questions]`.
6. **Khởi tạo và lưu phiên:** `InterviewService` tạo bản ghi `interview_sessions` (trạng thái ban đầu `CREATED`) và 6 bản ghi `interview_session_questions` với thứ tự `question_order` từ 1 đến 6 trong cơ sở dữ liệu `hirelens_interview` `[act_save_session]`.
7. **Hiển thị câu hỏi:** Frontend nhận phản hồi `SessionResponse`, cập nhật trạng thái phiên, hiển thị bong bóng chat câu hỏi đầu tiên (`currentIndex = 0`) gồm chủ đề, độ khó và nội dung câu hỏi `[merge_question]` → `[act_display_question]`.
8. **Ứng viên soạn và gửi câu trả lời:** Ứng viên nhập nội dung trả lời vào khung soạn thảo (tối đa 4.000 ký tự) và nhấn nút **"Gửi & nhận đánh giá"** `[merge_input]` → `[act_input_answer]`.
9. **Frontend kiểm tra dữ liệu đầu vào:** Frontend kiểm tra nội dung câu trả lời không được để trống `[dec_answer_valid: câu trả lời hợp lệ]`.
10. **Gửi câu trả lời lên máy chủ:** Frontend gọi `interviewsApi.submit(sessionId, questionId, answerText)` thông qua `POST /api/interviews/sessions/{id}/responses` `[act_submit_response]`.
11. **Khóa hàng phiên và kiểm tra quyền hạn:** `interview-service` thực thi truy vấn `sessionRepository.findForUpdate(sessionId)` với khóa bi quan (pessimistic lock) nhằm ngăn chặn xung đột ghi đồng thời, xác minh phiên thuộc quyền sở hữu của ứng viên và kiểm tra trạng thái phiên `[act_lock_session]` → `[dec_session_valid: phiên hợp lệ đang diễn ra]`.
12. **Cập nhật trạng thái và lấy rubric:** Service cập nhật thời điểm `startedAt`, chuyển trạng thái phiên thành `IN_PROGRESS`, lưu bản ghi `interview_responses` (trạng thái `SUBMITTED`). Đồng thời, service truy vấn bộ barem tiêu chí từ bảng `evaluation_rubrics` theo `questionId` (gồm 3 tiêu chí, trọng số, danh sách từ khóa gợi ý `expected_keywords`, các cách diễn đạt tham khảo `reference_answers` và ngộ nhận sai `misconceptions`) `[act_load_rubric]`.
13. **Gửi yêu cầu đánh giá sang interview-ai:** `AiScoringClient` chuẩn hóa trọng số tiêu chí (tổng bằng 1.0) và gửi request HTTP `POST /v1/interview/evaluate` với toàn bộ đáp án mẫu và barem từ CSDL sang `interview-ai` (cổng 8000) `[act_call_ai]`.
14. **Chấm điểm tại interview-ai:** `interview-ai` thực thi hàm `evaluate_question`:
    - Tính chỉ số tương đồng toàn câu BERTScore Precision, Recall, F1 giữa câu trả lời và đáp án mẫu tham khảo đầy đủ (`bert-base-multilingual-cased`).
    - Phân rã câu trả lời thành các mệnh đề khẳng định (`evidence_units`), đối chiếu ngữ nghĩa và đối chiếu từ khóa với từng tiêu chí rubric (`evaluate_rubric`).
    - Phát hiện các ngộ nhận sai (`misconceptions`) và chặn hành vi nhồi từ khóa (`keyword_only`).
    - Đánh giá mức độ đạt của từng tiêu chí (`covered`: 1.0, `partial`: 0.5, `missing` / `contradicted`: 0.0) và tính độ phủ `coverage_score`.
    - Trích xuất vector đặc trưng và dự đoán điểm qua mô hình hồi quy Ridge (`predict_score`).
    - Tổng hợp điểm số theo công thức kết hợp: `điểm = min(0.5 × điểm_Ridge + 5 × coverage, 10 × coverage + 2)` (chặn trong khoảng 0–10).
    - Tạo nhận xét giải thích tự động theo quy tắc (`build_comment`) `[act_score_ai]`.
15. **Kiểm tra phản hồi AI:** `AiScoringClient` nhận mã HTTP 200 và parse JSON kết quả `[dec_ai_status: chấm điểm thành công]`.
16. **Lưu kết quả đánh giá:** `InterviewService` lưu bản ghi `evaluation_results` chứa điểm số dự đoán (`predicted_score`), độ phủ (`coverage_score`), các điểm mạnh (`covered_points`), điểm cần bổ sung (`missing_points`), nhận xét (`feedback`), các chỉ số BERTScore P/R/F1 và chi tiết từng tiêu chí (`criterion_results`). Đồng thời, kiểm tra nếu tất cả câu hỏi đã được chấm thì chuyển trạng thái phiên sang `COMPLETED` và cập nhật `completedAt` `[act_save_evaluation]`.
17. **Hiển thị kết quả chấm điểm:** Frontend nhận `EvaluationResponse`, render giao diện `EvalBlock` gồm vòng tròn điểm số / 10, các chỉ số BERTScore Precision/Recall/F1, tỷ lệ phủ tiêu chí %, chi tiết điểm từng tiêu chí barem, nhận xét chi tiết và các thẻ chip gợi ý `[act_display_result]`.
18. **Kiểm tra tiến độ hoàn thành:**
    - **Nếu còn câu hỏi chưa hoàn thành:** Nút **"Câu tiếp theo"** được kích hoạt `[dec_completed: còn câu hỏi chưa hoàn thành]`. Ứng viên nhấn nút **"Câu tiếp theo"** `[act_click_next]`. Frontend tăng chỉ số câu hỏi `idx = session.currentIndex`, xóa nội dung soạn thảo cũ và hiển thị câu hỏi tiếp theo `[merge_question]` → `[act_display_question]`.
    - **Nếu đã hoàn thành toàn bộ câu hỏi trong phiên:** Trạng thái phiên là `COMPLETED`. Frontend hiển thị bảng **Tổng kết phiên** gồm số câu đã chấm, điểm trung bình toàn phiên và chi tiết điểm từng câu `[dec_completed: đã hoàn thành tất cả câu]` → `[act_display_summary]`.
19. **Kết thúc:** Ứng viên hoàn thành phiên ôn tập thành công `[final_node]`.

---

### 2.2. Các kịch bản ngoại lệ (Exception Flows)

#### Ngoại lệ 1: Ứng viên chưa có hồ sơ CV hoặc tài khoản không hợp lệ
- **Vị trí phát sinh:** `recruitment-service` (`InternalRecruitmentController.java:27-28`).
- **Nguyên nhân:** Ứng viên mới đăng ký chưa từng tải lên CV hoặc chưa mở trang hồ sơ để tạo bản ghi `candidate_profiles`.
- **Luồng xử lý:** Tại bước `[dec_context_valid]`, nhánh rẽ `[chưa có hồ sơ hoặc lỗi CV]` được kích hoạt. `recruitment-service` ném ngoại lệ `ApiException(HttpStatus.NOT_FOUND, "Candidate profile not found; open your CV first")`. Frontend bắt lỗi trong khối `catch` và hiển thị thông báo toast: *"Không tạo được phiên"* `[act_notify_context_err]`. Quá trình tạo phiên dừng lại `[final_node]`.

#### Ngoại lệ 2: Câu trả lời trống
- **Vị trí phát sinh:** Frontend (`CandidateInterviewPage.tsx:41`).
- **Nguyên nhân:** Ứng viên nhấn nút "Gửi & nhận đánh giá" nhưng chưa nhập nội dung hoặc chỉ nhập khoảng trắng.
- **Luồng xử lý:** Tại bước `[dec_answer_valid]`, điều kiện `[câu trả lời trống]` được kích hoạt. Frontend dừng gửi request, hiển thị thông báo toast cảnh báo: *"Hãy nhập câu trả lời"* `[act_notify_empty]`. Luồng quay trở lại ô nhập liệu `[merge_input]` để người dùng tiếp tục thao tác mà không bị mất trạng thái.

#### Ngoại lệ 3: Phiên đã hoàn thành hoặc xung đột trạng thái
- **Vị trí phát sinh:** `interview-service` (`InterviewService.java:111-112`).
- **Nguyên nhân:** Ứng viên gửi câu trả lời cho một phiên đã ở trạng thái `COMPLETED` (ví dụ do mở nhiều tab hoặc bấm submit lặp lại).
- **Luồng xử lý:** Tại bước `[dec_session_valid]`, nhánh rẽ `[phiên đã kết thúc hoặc không hợp lệ]` được kích hoạt. `interview-service` ném `ApiException(HttpStatus.CONFLICT, "Session completed; start another practice session")`. Frontend hiển thị toast báo lỗi: *"Đánh giá thất bại"* `[act_notify_session_err]`, không ghi đè kết quả `[final_node]`.

#### Ngoại lệ 4: Dịch vụ AI chấm điểm gặp lỗi hoặc mất kết nối
- **Vị trí phát sinh:** `interview-service` (`AiScoringClient.java:97-116`) và `interview-ai` (`AI/src/api.py:238-249`).
- **Nguyên nhân:** Tiến trình FastAPI chưa được khởi chạy, mô hình BERT chưa tải xong, calibration chưa được nạp, hoặc quá thời gian chờ (read timeout).
- **Luồng xử lý:** Tại bước `[dec_ai_status]`, nhánh rẽ `[AI lỗi hoặc mất kết nối]` được kích hoạt. `AiScoringClient` ném lỗi HTTP 502 Bad Gateway hoặc 503 Service Unavailable. Toàn bộ transaction tại `InterviewService.submitAndEvaluate` được rollback hoàn toàn (không lưu câu trả lời giả mạo hay điểm rỗng vào database). Frontend hiển thị toast: *"Đánh giá thất bại"* `[act_notify_ai_err]`. Phiên giữ nguyên trạng thái an toàn `[final_node]`.

---

## 3. Bảng truy vết phần tử (Traceability Matrix)

| STT | Mã Node (`key`) | Loại Node (`kind`) | Làn (`partition`) | Tên hiển thị trên biểu đồ | Nguồn truy vết trong mã nguồn (`src`) |
|:---:|:---|:---|:---|:---|:---|
| 1 | `init` | initial | `user` | Khởi đầu | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:65` |
| 2 | `act_click_start` | action | `user` | Yêu cầu bắt đầu phiên ôn tập | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:31` |
| 3 | `act_send_create_session` | action | `fe` | Gửi yêu cầu tạo phiên phỏng vấn | `source/recruit_system/frontend/src/api/client.ts:129` |
| 4 | `act_get_context` | action | `recruitment_svc` | Truy vấn ngữ cảnh JD và kỹ năng CV | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/InternalRecruitmentController.java:21` |
| 5 | `dec_context_valid` | decision | `recruitment_svc` | Kiểm tra hồ sơ ứng viên? | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/InternalRecruitmentController.java:27` |
| 6 | `act_notify_context_err` | action | `fe` | Hiển thị thông báo lỗi hồ sơ | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:37` |
| 7 | `act_select_questions` | action | `interview_svc` | Chọn bộ câu hỏi theo kỹ năng và cấp độ | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/QuestionSelectionService.java:26` |
| 8 | `act_save_session` | action | `interview_svc` | Khởi tạo và lưu phiên vào CSDL | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:73` |
| 9 | `merge_question` | merge | `fe` | Hợp nhất luồng hiển thị câu hỏi | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:22` |
| 10 | `act_display_question` | action | `fe` | Hiển thị câu hỏi phỏng vấn | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:71` |
| 11 | `merge_input` | merge | `user` | Hợp nhất luồng nhập câu trả lời | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:75` |
| 12 | `act_input_answer` | action | `user` | Nhập câu trả lời và nhấn gửi | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:75` |
| 13 | `dec_answer_valid` | decision | `fe` | Kiểm tra nội dung câu trả lời? | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:41` |
| 14 | `act_notify_empty` | action | `fe` | Hiển thị cảnh báo yêu cầu nhập nội dung | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:41` |
| 15 | `act_submit_response` | action | `fe` | Gửi câu trả lời để chấm điểm | `source/recruit_system/frontend/src/api/client.ts:140` |
| 16 | `act_lock_session` | action | `interview_svc` | Khóa hàng phiên và kiểm tra quyền | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:108` |
| 17 | `dec_session_valid` | decision | `interview_svc` | Kiểm tra trạng thái phiên? | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:111` |
| 18 | `act_notify_session_err` | action | `fe` | Hiển thị thông báo phiên đã kết thúc | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:47` |
| 19 | `act_load_rubric` | action | `interview_svc` | Truy xuất đáp án mẫu và tiêu chí rubric | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:165` |
| 20 | `act_call_ai` | action | `interview_svc` | Gửi yêu cầu đánh giá sang AI | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/AiScoringClient.java:85` |
| 21 | `act_score_ai` | action | `ai_svc` | Tính điểm BERTScore, rubric và hồi quy Ridge | `source/recruit_system/AI/src/scoring.py:62` |
| 22 | `dec_ai_status` | decision | `interview_svc` | Kiểm tra phản hồi dịch vụ AI? | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/AiScoringClient.java:97` |
| 23 | `act_notify_ai_err` | action | `fe` | Hiển thị thông báo lỗi dịch vụ AI | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:47` |
| 24 | `act_save_evaluation` | action | `interview_svc` | Lưu kết quả chấm và cập nhật tiến độ phiên | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:179` |
| 25 | `act_display_result` | action | `fe` | Hiển thị điểm số, tiêu chí và nhận xét | `source/recruit_system/frontend/src/components/common/EvalBlock.tsx:24` |
| 26 | `dec_completed` | decision | `fe` | Đã hoàn thành toàn bộ câu hỏi? | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:78` |
| 27 | `act_click_next` | action | `user` | Chọn chuyển sang câu hỏi tiếp theo | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:50` |
| 28 | `act_display_summary` | action | `fe` | Hiển thị tổng kết kết quả phiên ôn tập | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:82` |
| 29 | `final_node` | final | `user` | Kết thúc hoạt động | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:72` |

**Tổng số node:** 29 (Thỏa mãn giới hạn $\le 30$ node của đề bài).  
**Số phân vùng (Swimlanes):** 5 (`Người dùng`, `Frontend`, `recruitment-service`, `interview-service`, `interview-ai`).

---

## 4. Bảng truy vết luồng chuyển tiếp (Flows Matrix)

| STT | Từ Node (`from`) | Tới Node (`to`) | Điều kiện rẽ nhánh (`guard`) | Nguồn truy vết (`src`) |
|:---:|:---|:---|:---|:---|
| 1 | `init` | `act_click_start` | | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:65` |
| 2 | `act_click_start` | `act_send_create_session` | | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:34` |
| 3 | `act_send_create_session` | `act_get_context` | | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:48` |
| 4 | `act_get_context` | `dec_context_valid` | | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/InternalRecruitmentController.java:27` |
| 5 | `dec_context_valid` | `act_notify_context_err` | `[chưa có hồ sơ hoặc lỗi CV]` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/InternalRecruitmentController.java:28` |
| 6 | `dec_context_valid` | `act_select_questions` | `[hồ sơ hợp lệ]` | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:68` |
| 7 | `act_notify_context_err` | `final_node` | | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:37` |
| 8 | `act_select_questions` | `act_save_session` | | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:73` |
| 9 | `act_save_session` | `merge_question` | | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:94` |
| 10 | `merge_question` | `act_display_question` | | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:22` |
| 11 | `act_display_question` | `merge_input` | | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:75` |
| 12 | `merge_input` | `act_input_answer` | | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:75` |
| 13 | `act_input_answer` | `dec_answer_valid` | | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:41` |
| 14 | `dec_answer_valid` | `act_notify_empty` | `[câu trả lời trống]` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:41` |
| 15 | `dec_answer_valid` | `act_submit_response` | `[câu trả lời hợp lệ]` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:44` |
| 16 | `act_notify_empty` | `merge_input` | | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:41` |
| 17 | `act_submit_response` | `act_lock_session` | | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:108` |
| 18 | `act_lock_session` | `dec_session_valid` | | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:111` |
| 19 | `dec_session_valid` | `act_notify_session_err` | `[phiên đã kết thúc hoặc không hợp lệ]` | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:112` |
| 20 | `dec_session_valid` | `act_load_rubric` | `[phiên hợp lệ đang diễn ra]` | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:123` |
| 21 | `act_notify_session_err` | `final_node` | | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:47` |
| 22 | `act_load_rubric` | `act_call_ai` | | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:169` |
| 23 | `act_call_ai` | `act_score_ai` | | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/AiScoringClient.java:86` |
| 24 | `act_score_ai` | `dec_ai_status` | | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/AiScoringClient.java:97` |
| 25 | `dec_ai_status` | `act_notify_ai_err` | `[AI lỗi hoặc mất kết nối]` | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/AiScoringClient.java:99` |
| 26 | `dec_ai_status` | `act_save_evaluation` | `[chấm điểm thành công]` | `source/recruit_system/backend/interview-service/src/main/java/recruit/demo/service/InterviewService.java:176` |
| 27 | `act_notify_ai_err` | `final_node` | | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:47` |
| 28 | `act_save_evaluation` | `act_display_result` | | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:44` |
| 29 | `act_display_result` | `dec_completed` | | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:78` |
| 30 | `dec_completed` | `act_click_next` | `[còn câu hỏi chưa hoàn thành]` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:78` |
| 31 | `dec_completed` | `act_display_summary` | `[đã hoàn thành tất cả câu]` | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:82` |
| 32 | `act_click_next` | `merge_question` | | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:52` |
| 33 | `act_display_summary` | `final_node` | | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:72` |

**Tổng số flow:** 33. Mọi Decision đều có guard trên tất cả nhánh ra.

---

## 5. Mâu thuẫn giữa tài liệu và mã nguồn (Discrepancies)

1. **Mô hình kiến trúc triển khai:**
   - *Tài liệu báo cáo v6:* Mô tả toàn bộ chức năng nằm trong một ứng dụng Spring Boot nguyên khối (Monolith) dùng chung một CSDL duy nhất.
   - *Mã nguồn thực tế (commit `1c96706`):* Đã chuyển hoàn toàn sang **Microservices**:
     - `interview-service` (cổng 8083, CSDL `hirelens_interview`) quản lý ngân hàng câu hỏi, phiên và kết quả chấm.
     - `recruitment-service` (cổng 8082, CSDL `hirelens_recruitment`) quản lý hồ sơ ứng viên và tin tuyển dụng.
     - `interview-ai` (cổng 8000) chạy FastAPI độc lập phục vụ chấm điểm.
     - Giao tiếp giữa các service sử dụng HTTP REST nội bộ bảo vệ bởi shared token `X-Service-Token`.
   - *Quyết định:* Vẽ hoàn toàn theo kiến trúc Microservices thực tế trong mã nguồn theo chỉ đạo của kiến trúc sư dự án.

2. **Cơ chế fallback khi AI gặp sự cố:**
   - *Tài liệu cũ / giả định ban đầu:* Có thể dùng rule-based fallback để tính điểm cơ bản khi AI ngoại tuyến.
   - *Mã nguồn thực tế (`AiScoringClient.java:46`, `application.yml:44`):* Thuộc tính `fallback-to-rule: false` được viết cứng. Khi AI ngoại tuyến hoặc lỗi, client ném ngay lỗi `503 Service Unavailable` hoặc `502 Bad Gateway`, không tự ý tính điểm thay thế bằng rule để tránh làm sai lệch kết quả đánh giá năng lực của ứng viên.

3. **Cơ chế chấm điểm và sinh nhận xét:**
   - *Kỳ vọng thường thấy:* Gọi LLM (như ChatGPT/OpenAI) để sinh nhận xét tự do.
   - *Mã nguồn thực tế (`docs/Module3_Interview_Flow.md`, `AI/src/scoring.py:46-59`):* Không gọi LLM thời gian thực. Hệ thống sử dụng mô hình tất định: BERTScore + Barem Rubric phân rã mệnh đề + Hồi quy Ridge Calibration, nhận xét được ghép từ tập quy tắc có sẵn dựa trên các ý đạt và ý thiếu thực tế.

---

## 6. Điểm cần xác nhận (Open Questions)

1. **Điều hướng khi thiếu hồ sơ ứng viên:** Khi ứng viên nhấn nút bắt đầu ôn tập mà chưa từng tải lên hoặc khởi tạo hồ sơ CV trong hệ thống, `recruitment-service` ném lỗi HTTP 404 và frontend hiển thị thông báo toast lỗi. Cần xác nhận xem có nên bổ sung luồng tự động chuyển hướng ứng viên sang màn hình quản lý CV (`/candidate/cv`) thay vì chỉ hiện thông báo lỗi hay không.
2. **Hỗ trợ cấp độ câu hỏi Senior:** Ngân hàng câu hỏi v2 trong database hiện chỉ bao gồm 30 câu hỏi chuẩn hóa với 3 cấp độ: `Intern`, `Junior`, `Middle`. Đối với các tin tuyển dụng cấp độ `Senior` hoặc `Lead`, hệ thống hiện tại đang tự động ánh xạ mục tiêu về cấp độ `Middle`. Cần xác nhận thời điểm bổ sung bộ câu hỏi chuẩn dành riêng cho cấp độ Senior trong các phiên bản tiếp theo.
