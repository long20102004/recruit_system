# Các tính năng còn thiếu

Cập nhật: 27/11/2026. Gộp từ danh sách tính năng hệ thống và `TASKS_ai_service.md` (24/11/2026).

Danh sách các tính năng chưa hoàn thiện, chia theo **module AI** đã phân công (M1, M2, M3). Tính năng không thuộc module AI nào xếp vào nhóm **Chung**.

Phần lớn tính năng hệ thống đã có giao diện theo design canvas và đang chạy bằng **dữ liệu mẫu** (`frontend/src/api/mock/`). Mỗi hàm mock có chữ ký giống API thật, trả Promise, nên khi làm backend chỉ cần thay phần thân hàm, giữ nguyên chữ ký; trang FE không phải sửa. Mã màn (C01, R06, AD02…) theo design canvas HireLens UI Redesign.

## Module

| Module | Phạm vi | Phụ trách | Thư mục AI |
|---|---|---|---|
| **M1 · Trích xuất CV** | Đọc CV, chuẩn hoá kỹ năng, quản lý CV | Hocnv | `ai-service/extraction/` |
| **M2 · Matching và gợi ý** | Xếp hạng CV–tin, gợi ý việc, tìm CV, job alert | nguyenloc | `ai-service/matching/` |
| **M3 · Phỏng vấn** | Phiên phỏng vấn, chấm điểm, ngân hàng câu hỏi, lời mời phỏng vấn | longhh | `ai-service/interview/service/` |
| **Chung** | Công ty, đơn ứng tuyển, tin tuyển dụng, thông báo, quản trị | Chưa gán | — |

Service backend nơi đặt bảng và API của từng tính năng ghi ở dòng **Service chính / Service liên quan**:

| Service | Đang quản lý | Route qua gateway |
|---|---|---|
| **identity-service** (8081) | Người dùng, đăng nhập, RBAC, tài khoản, cài đặt thông báo, nhật ký hoạt động (`audit_logs`), dashboard admin | `/api/auth/**`, `/api/account/**`, `/api/admin/users/**`, `/api/admin/roles/**`, `/api/admin/dashboard/**`, `/api/admin/audit-logs/**` |
| **recruitment-service** (8082) | Công ty, tin tuyển dụng, đơn ứng tuyển, CV, matching, dashboard, việc đã lưu, kiểm duyệt tin | `/api/jobs/**`, `/api/cvs/**`, `/api/applications/**`, `/api/matching/**`, `/api/dashboard/**`, `/api/companies/**`, `/api/recruiter/company/**`, `/api/admin/companies/**`, `/api/admin/jobs/**`, `/api/saved-jobs/**` |
| **interview-service** (8083) | Ngân hàng câu hỏi, phiên phỏng vấn, chấm điểm | `/api/interviews/**` |
| **ai-service** | Trích xuất CV, matching CV–tin, chấm câu trả lời | Gọi nội bộ từ recruitment/interview |
| **notification** (mới) | Thông báo trong app và email | Chưa có |
| **api-gateway** | Định tuyến | Mỗi nhóm API mới cần thêm route |

Ký hiệu cho task AI:
- **Ưu tiên:** P0 = cần cho demo / bảo vệ, P1 = nên có, P2 = làm nếu còn thời gian.
- **KL (khối lượng):** S ≤ 1 ngày, M 2–3 ngày, L ≥ 4 ngày.
- **Nguồn:** mã trong `PLAN_chuc_nang_he_thong.md`, hoặc *Mới* nếu là đề xuất bổ sung ở file này.

## Tổng quan tính năng hệ thống

| # | Tính năng | Module | Service chính | Task AI liên quan | Màn | Hiện trạng | Phụ thuộc |
|---|---|---|---|---|---|---|---|
| 2 | Thành viên công ty & lời mời | Chung | recruitment | — | R10, C13 | Mock | 1 |
| 5 | Module thông báo | Chung | notification (mới) | — | C13, chuông thông báo, C14 | Mock | — |
| 7 | Job alert | M2 | recruitment | F2-07 | C09, C01 | Mock | 5 |
| 8 | Nhiều CV cho mỗi ứng viên | M1 | recruitment | F1-02, F1-04 | C02, C05 | Mock | — |
| 9 | Tìm & lưu CV ứng viên | M2 | recruitment | F2-05 | R11 | Mock | 8 |
| 10 | Mời phỏng vấn & xem kết quả phỏng vấn | M3 | interview | F3-01, F3-04, F3-05, F3-09 | R08, C10, C01, R06 | Mock | 3 |
| 14 | Ngân hàng câu hỏi & mẫu CV cho admin | M3 + Chung | interview, recruitment | F3-03 | AD05, AD06 | Danh sách câu hỏi thật, chỉnh sửa là mock | — |
| 15 | Bổ sung cho phiên phỏng vấn | M3 | interview | F3-06 | C10, C11, C12 | Thiếu chức năng | — |

## Đã có

| Module | Chức năng đã chạy |
|---|---|
| M1 · Trích xuất CV | Upload CV PDF → trích xuất thông tin, kỹ năng (kèm liên kết KB) → ứng viên chỉnh sửa → lưu (CV-01) |
| M2 · Matching | Ứng viên xem việc phù hợp và làm mới (MT-01); recruiter xếp hạng ứng viên của một tin (MT-02); chi tiết điểm matching (MT-03) |
| M3 · Phỏng vấn | Tạo phiên luyện theo JD/CV (IV-01); chấm câu trả lời bằng BERTScore + rubric (IV-02); lịch sử và tổng kết phiên (IV-03); recruiter xem ngân hàng câu hỏi (IV-04) |
| Chung | Quản lý & duyệt công ty (#1); xử lý đơn ứng tuyển, lịch sử, rút đơn, ghi chú/chấm sao & tải CV (#3); sửa tin, gia hạn, xoá nháp & tự hết hạn (#4); việc đã lưu (#6); dashboard recruiter đầy đủ (#11); dashboard & audit log admin (#12); kiểm duyệt khoá/mở khoá tin (#13) |

---

## M1 · Trích xuất CV (Hocnv)

### 8. Nhiều CV cho mỗi ứng viên

**Module:** **M1 · Trích xuất CV** (F1-02, F1-04).  
**Service chính:** recruitment-service (bảng `cv_documents`, `candidate_profiles`).  
**Service liên quan:** ai-service: trích xuất cho từng CV, matching theo CV chính.

**Màn:** C02 Quản lý CV, C05 chọn CV khi ứng tuyển (hiện chỉ có 1 CV).  
**Mock:** `candidateMock.ts` (`cvsMock.list`, `setMain`, `remove`).

- **Quản lý CV:** tối đa 5 CV; đặt một CV làm "CV chính" (dùng cho matching và gợi ý việc); đổi tên; tải file gốc; xoá.
- **Không xoá được** CV đang gắn với một đơn ứng tuyển chưa kết thúc.
- **Ứng tuyển:** chọn CV gửi kèm, hiện % phù hợp của từng CV với tin.
- **Tạo CV từ form** (nút "Tạo CV từ đầu") ngoài cách tải PDF lên, dùng mẫu CV của tính năng 14.

**Cần làm ở backend**
- Đổi model `cv_documents` / `candidate_profiles` từ quan hệ 1–1 sang 1–nhiều, thêm cờ `is_main`.
- Matching chạy theo CV chính; đơn ứng tuyển lưu `cv_document_id` (field đã có).
- Đây là thay đổi lớn ở recruitment-service và luồng AI extraction.

#### Task AI của M1

| ID | Chức năng còn thiếu | Actor | Phần AI | Phần backend / FE | Ưu tiên | KL | Nguồn |
|---|---|---|---|---|---|---|---|
| F1-01 | Trích xuất CV chạy nền: upload xong trả về ngay, FE hiển thị “Đang xử lý” rồi tự cập nhật | Ứng viên | Giữ API sync; đảm bảo gọi lại cùng file cho cùng kết quả | recruitment: `@Async` + `parsing_status` (enum đã có); FE poll | P1 | M | INF-07 |
| F1-02 | Trích xuất từ nhiều CV của một ứng viên (tối đa 5, chọn CV chính) | Ứng viên | Không đổi API; gắn `cv_id` vào kết quả | recruitment: CV-04, CV-05; FE danh sách thẻ CV | P1 | L | CV-04, CV-05 |
| F1-03 | Nhận CV dạng DOCX và PDF scan (ảnh) | Ứng viên | Đọc DOCX; OCR cho PDF không có lớp chữ; trả lỗi rõ khi không đọc được | FE: thêm định dạng cho ô upload, hiển thị lỗi | P1 | M | Mới |
| F1-04 | Tạo CV từ form khi chưa có file, vẫn chuẩn hoá kỹ năng như CV upload | Ứng viên | Endpoint chuẩn hoá kỹ năng / kinh nghiệm từ dữ liệu form (dùng KB sẵn có) | recruitment + FE: form nhập từ đầu | P1 | S | CV-03 |
| F1-05 | Tự điền form đăng tin từ mô tả JD dán vào (kỹ năng, cấp độ, số năm kinh nghiệm) | Recruiter | Endpoint trích xuất JD → các trường của tin | FE trang đăng tin: nút “Tự điền từ mô tả” | P2 | M | Mới |
| F1-06 | Nhận xét chất lượng CV: thiếu mục, thiếu số liệu, kỹ năng chưa khớp với vị trí mong muốn | Ứng viên | Luật dựa trên output trích xuất + KB | FE: khối “Gợi ý cải thiện CV” trên trang CV | P2 | M | Mới |

---

## M2 · Matching và gợi ý (nguyenloc)

### 7. Job alert

**Module:** **M2 · Matching và gợi ý** (F2-07). Phần lưu alert, giao diện và gửi thông báo thuộc nhóm Chung (tính năng 5).  
**Service chính:** recruitment-service (khớp với tin tuyển dụng).  
**Service liên quan:** notification: gửi thông báo và email theo tần suất.

**Màn:** C09 Job alert, thẻ Job alert ở C01.  
**Mock:** `candidateMock.ts` (`jobAlertsMock.list`, `create`, `update`, `toggle`, `remove`).

- **Tạo alert:** tên, từ khoá/kỹ năng, thành phố, cấp bậc, lương tối thiểu, kênh nhận (trong app, email), tần suất (ngay khi có tin mới, hoặc gom một email mỗi ngày). Mỗi người tối đa 5 alert.
- **Quản lý alert:** bật/tắt, sửa, xoá; hiện số tin khớp trong tuần.
- **Khớp tin:** khi có tin mới được đăng, hoặc theo lịch hằng ngày, tìm các alert khớp rồi gửi thông báo qua tính năng 5.

**Cần làm ở backend:** bảng `job_alerts`, API CRUD, bộ khớp tin (lắng nghe sự kiện đăng tin, kèm job chạy hằng ngày để gom mail). Phụ thuộc tính năng 5.

### 9. Tìm và lưu CV ứng viên (headhunt)

**Module:** **M2 · Matching và gợi ý** (F2-05).  
**Service chính:** recruitment-service (hồ sơ ứng viên và cờ `open_to_work` đặt ở `candidate_profiles`).  
**Service liên quan:** ai-service: xếp hạng CV theo tin (dùng lại matching phạm vi "pool").

**Màn:** R11 Tìm & lưu CV.  
**Mock:** `recruiterMock.ts` (`listCandidateCvs`, `toggleSaveCv`, `updateCvNote`).

- **Cho phép bị tìm thấy:** ứng viên bật "Đang tìm việc" mới xuất hiện trong kết quả. Thông tin liên hệ bị ẩn cho tới khi ứng viên ứng tuyển vào công ty.
- **Tìm kiếm:** theo kỹ năng, chức danh, thành phố, số năm kinh nghiệm; có thể chọn một tin để xếp hạng theo độ phù hợp với tin đó.
- **Lưu CV:** lưu kèm ghi chú nội bộ, có tab "CV đã lưu".

**Cần làm ở backend**
- Cờ `open_to_work` cho ứng viên (thêm một mục bật/tắt ở C14).
- API tìm kiếm (dùng lại AI matching với phạm vi "pool" đã có).
- Bảng `saved_candidates`.

#### Task AI của M2

| ID | Chức năng còn thiếu | Actor | Phần AI | Phần backend / FE | Ưu tiên | KL | Nguồn |
|---|---|---|---|---|---|---|---|
| F2-01 | Gợi ý việc làm tự động, tính trước theo lịch, chỉ tính lại khi CV hoặc tin đổi | Ứng viên | Chấm 1 CV với nhiều tin trong một lần gọi (dùng `POST /match/cv/{id}` hoặc thêm batch) | recruitment: `@Scheduled`, bảng kết quả, content hash | P1 | L | RS-01 |
| F2-02 | Đánh giá chất lượng gợi ý (MRR, NDCG@K, HitRate@K) cho báo cáo | — | Tập nhãn + script xuất bảng từ `cvmatch.evaluation` (module đã có) | — | P1 | M | RS-02 |
| F2-03 | Điểm matching trong chi tiết đơn ứng tuyển: kỹ năng khớp, kỹ năng thiếu | Recruiter | Dùng `/explain` sẵn có; trả dạng gọn cho FE | recruitment + FE: drawer chi tiết đơn | P0 | S | AP-05 |
| F2-04 | Tin bị đóng, hết hạn hoặc CV bị xoá không còn xuất hiện trong gợi ý và xếp hạng | Hệ thống | Thêm `DELETE /jd/{id}` (đã có `DELETE /cv/{id}`) | recruitment: gọi khi đóng tin / xoá CV | P1 | S | JB-03, CV-05 |
| F2-05 | Recruiter tìm CV ứng viên đang mở tìm việc theo kỹ năng hoặc mô tả | Recruiter | Truy vấn vector trên CV có `is_open_for_job` | recruitment: `GET /api/cvs/search`, CV-09; FE trang tìm CV | P2 | M | RS-03, CV-09 |
| F2-06 | “Việc làm tương tự” trên trang chi tiết tin | Ứng viên | Tìm tin gần nhất theo embedding JD | FE: khối gợi ý cuối trang tin | P2 | S | Mới |
| F2-07 | Thông báo việc làm mới phù hợp (job alert) | Ứng viên | Chấm tin mới với các CV đang mở tìm việc, trả danh sách vượt ngưỡng | recruitment phát sự kiện `JobPublished`; notification-service gửi thông báo | P2 | M | Mới, cần NT-01 |
| F2-08 | Xếp hạng ứng viên kết hợp điểm matching và điểm phỏng vấn | Recruiter | Công thức kết hợp, trọng số cấu hình được | recruitment: EV-02 lưu `interview_score`; FE cột sắp xếp | P1 | S | EV-02 |

F2-06 ("Việc làm tương tự"): FE đã có khối này ở trang chi tiết việc, hiện đang chọn theo số kỹ năng bắt buộc trùng nhau. Khi có API embedding thì thay bằng kết quả từ M2.

---

## M3 · Phỏng vấn (longhh)

### 10. Mời phỏng vấn và xem kết quả phỏng vấn

**Module:** **M3 · Phỏng vấn** (F3-01, F3-04, F3-05, F3-09).  
**Service chính:** interview-service (lời mời và phiên phỏng vấn).  
**Service liên quan:** recruitment-service: đơn ứng tuyển chuyển sang `INTERVIEW`, kiểm tra recruiter có thuộc công ty nhận đơn. notification: gửi lời mời và nhắc ứng viên.

**Màn:** R08 Kết quả phỏng vấn, phần "Lời mời từ nhà tuyển dụng" ở C10, thẻ lời mời ở C01, phần "Kết quả phỏng vấn" ở R06.  
**Mock:** `recruiterMock.ts` (`getRecruiterInterviewResults`, `remindInterviewCandidate`).

- **Gửi lời mời:** recruiter mời ứng viên của một đơn làm phiên phỏng vấn AI, chọn số câu và hạn làm. Đơn tự chuyển sang trạng thái `INTERVIEW`.
- **Phía ứng viên:** thấy lời mời ở C10/C01 rồi làm phiên. Kết quả gửi về công ty (C12 có nhãn "Đã gửi cho …").
- **Phía recruiter (R08):**
  - Thống kê: lời mời đã gửi, số đã hoàn thành, số đang chờ, điểm trung bình.
  - Bảng gồm ứng viên, tin, thời điểm mời, trạng thái (Chờ làm / Đang làm / Hoàn thành / Đã huỷ), điểm, chủ đề yếu nhất.
  - Thao tác: nhắc ứng viên, xem chi tiết phiên.

**Cần làm ở backend**
- Bảng `interview_invitations` trong interview-service.
- API cho recruiter xem phiên phỏng vấn của ứng viên đã ứng tuyển vào công ty mình (quyền `interview:read-all` hiện chỉ cấp cho admin).
- Nối với luồng đổi trạng thái đơn (tính năng 3).

### 14. Ngân hàng câu hỏi và mẫu CV cho admin

**Module:** Ngân hàng câu hỏi và rubric thuộc **M3 · Phỏng vấn** (F3-03); mẫu CV thuộc nhóm Chung.  
**Service chính:** interview-service (câu hỏi, rubric); recruitment-service (mẫu CV, đi cùng tính năng nhiều CV).  
**Service liên quan:** api-gateway: route `/api/admin/questions/**` và `/api/admin/cv-templates/**`.

**Màn:** AD05 Ngân hàng câu hỏi (danh sách thật, chỉnh sửa là mock), AD06 Mẫu CV.  
**Mock:** `questionBankMock.ts` (`list`, `create`, `update`, `setApproved`, `setEnabled`), `adminMock.ts` (`listCvTemplates`, `createCvTemplate`, `updateCvTemplate`, `deleteCvTemplate`).

- **Ngân hàng câu hỏi:**
  - Thêm và sửa câu hỏi: nội dung, chủ đề, cấp độ, dạng (Kiến thức / Áp dụng / Tình huống), đáp án tham khảo.
  - Rubric gồm nhiều tiêu chí, mỗi tiêu chí có trọng số (tổng 100%), ý đúng, từ khoá gợi ý, ngộ nhận cần phát hiện.
  - Duyệt bởi chuyên gia (Cần duyệt / Đã duyệt; sửa xong phải duyệt lại); bật/tắt câu hỏi.
  - Nhà tuyển dụng chỉ xem.
- **Mẫu CV:** tạo, sửa, ẩn hoặc xoá mẫu CV dùng cho tính năng "Tạo CV từ đầu" (tính năng 8): bố cục, các mục, màu nhấn.

**Cần làm ở backend**
- API CRUD câu hỏi và rubric trong interview-service. Bảng câu hỏi đã có, cần thêm trường dạng câu hỏi, trạng thái duyệt và cấu trúc rubric.
- Bảng `cv_templates` và API CRUD.

### 15. Bổ sung cho phiên phỏng vấn

**Module:** **M3 · Phỏng vấn** (F3-06 gợi ý ôn tập). Các phần còn lại (lọc khi tạo phiên, bỏ qua câu, xuất PDF) cũng giao M3.  
**Service chính:** interview-service.  
**Service liên quan:** ai-service: đánh giá tổng quan phiên.

**Màn:** C10 Phỏng vấn, C11 Phiên phỏng vấn, C12 Tổng kết phiên.

- **Ở C10:** lọc chủ đề ưu tiên, cấp độ và loại câu hỏi khi tạo phiên luyện tập. Hiện chỉ chọn được số câu.
- **Ở C11:** nút "Bỏ qua câu này".
- **Ở C12:** tải báo cáo phiên dạng PDF; hiện thời lượng phiên; đánh giá tổng quan bằng AI.

**Cần làm ở backend**
- Mở rộng request tạo phiên và cách chọn câu hỏi.
- API bỏ qua câu, API xuất PDF.
- Lưu thời điểm bắt đầu và kết thúc phiên.

#### Task AI của M3

| ID | Chức năng còn thiếu | Actor | Phần AI | Phần backend / FE | Ưu tiên | KL | Nguồn |
|---|---|---|---|---|---|---|---|
| F3-01 | Recruiter xem kết quả phỏng vấn của ứng viên ứng tuyển tin của mình | Recruiter | — | interview: API liệt kê phiên theo tin / ứng viên; FE panel “Phiên gần nhất” | P0 | M | IV-05 |
| F3-02 | Chấm câu trả lời chạy nền, không treo request tới 180 giây | Ứng viên | Load model một lần, cache embedding đáp án mẫu; chấm idempotent theo `answer_id` | interview: `PENDING` + `@Async`; FE poll | P1 | M | INF-06 |
| F3-03 | Admin CRUD câu hỏi và rubric; câu mới chấm được ngay | Admin | `/v1/interview/evaluate` nhận rubric trong request thay vì chỉ đọc file barem; endpoint kiểm tra rubric hợp lệ | interview: API CRUD, `review_status`; FE trang ngân hàng câu hỏi | P1 | M | IV-07 |
| F3-04 | Lời mời phỏng vấn khi đơn chuyển sang `INTERVIEW`; huỷ khi đơn bị rút, từ chối hoặc tin đóng | Recruiter → Ứng viên | Chọn bộ câu hỏi theo JD của tin và CV của đơn | interview: consumer RabbitMQ, bảng `interview_invitations`; FE danh sách lời mời | P1 | M | IV-06, IV-10 |
| F3-05 | Gửi kết quả phiên về đơn ứng tuyển khi phiên hoàn thành | Hệ thống | Trả điểm tổng và điểm theo kỹ năng | interview phát `InterviewCompleted`; recruitment EV-02 | P1 | S | IV-11, EV-02 |
| F3-06 | Gợi ý ôn tập sau phiên: kỹ năng yếu, ý hay thiếu, câu nên luyện lại | Ứng viên | Tổng hợp “ý thiếu” và điểm theo kỹ năng của cả phiên | FE: khối gợi ý trong trang tổng kết | P2 | S | Mới |
| F3-07 | Bộ câu hỏi và barem cấp Senior | — | Thêm barem vào `rubric-templates/` | interview: migration dữ liệu | P2 | M | IV-08 |
| F3-08 | Đánh giá chất lượng chấm so với người chấm (Pearson, Spearman, MAE) | — | Tập câu trả lời có điểm người chấm + script đánh giá | — | P2 | M | IV-09 |
| F3-09 | Cập nhật quyền xem kết quả khi recruiter rời công ty | Hệ thống | — | interview: consumer `CompanyMemberRemoved` | P2 | S | IV-12 |

---

## Chung (chưa gán module AI)

Các tính năng nhóm Chung còn lại cần triển khai:

### 2. Thành viên công ty và lời mời

**Module:** Chung (chưa gán module AI).  
**Service chính:** recruitment-service (thành viên gắn với công ty).  
**Service liên quan:** identity-service: API nội bộ tra người dùng theo email khi mời (gọi qua OpenFeign `IdentityServiceClient`). notification: gửi lời mời và kết quả chấp nhận/từ chối.

**Màn:** R10 Thành viên; lời mời hiện trong C13 Thông báo.  
**Mock:** `recruiterMock.ts` (`getTeamData`, `updateMemberRole`, `removeTeamMember`, `inviteTeamMember`, `resendTeamInvite`, `revokeTeamInvite`), `candidateMock.ts` (`notificationsMock.respondInvite`).

- **Vai trò trong công ty:**

  | Vai trò | Quyền |
  |---|---|
  | Owner | Toàn quyền, chuyển quyền sở hữu |
  | Manager | Sửa công ty, mời thành viên, đăng tin, xử lý đơn |
  | Recruiter | Đăng tin, xử lý đơn, mời phỏng vấn |
  | Viewer | Chỉ xem tin và đơn |

- **Mời thành viên:**
  - Mời bằng email; người được mời phải đã có tài khoản.
  - Lời mời hết hạn sau 7 ngày; có thể gửi lại hoặc thu hồi.
  - Người được mời nhận thông báo và bấm Chấp nhận hoặc Từ chối.
- **Kiểm tra khi mời:** email chưa có tài khoản, người đó đã là thành viên, hoặc đã có lời mời đang chờ.
- **Quản lý thành viên:** đổi vai trò, xoá thành viên (không xoá được Owner).

**Cần làm ở backend**
- Bảng `company_members` và `company_invitations`.
- Phân quyền theo vai trò trong công ty, chạy song song với RBAC hệ thống hiện có.
- Tin tuyển dụng và đơn ứng tuyển phải thuộc về **công ty**, không chỉ thuộc về người tạo như hiện nay (`createdById`).

### 5. Module thông báo

**Module:** Chung (chưa gán module AI).  
**Service chính:** notification (mới). Có thể tách service mới hoặc đặt trong identity-service, nơi đã có `notification_preferences` và mailer.  
**Service liên quan:** recruitment-service và interview-service: gửi sự kiện (đổi trạng thái đơn, lời mời, job alert, AI đọc xong CV, duyệt công ty, khoá tin). identity-service: cài đặt thông báo, email người nhận. api-gateway: route `/api/notifications/**`.

**Màn:** C13 Thông báo, chuông thông báo trên menu ứng viên. C14 "Cài đặt thông báo" đã lưu được lựa chọn nhưng chưa có tác dụng.  
**Mock:** `candidateMock.ts` (`notificationsMock.list`, `unreadCount`, `markRead`, `markAllRead`, `respondInvite`).

- **Thông báo trong app:** danh sách có tab Tất cả / Chưa đọc / Ứng tuyển / Phỏng vấn / Job alert / Công ty; đánh dấu đã đọc từng cái hoặc tất cả; đếm số chưa đọc trên chuông; phân trang "Xem thêm".
- **Sự kiện tạo thông báo:** đơn đổi trạng thái, có lời mời phỏng vấn, job alert khớp tin mới, lời mời tham gia công ty, AI đọc CV xong, công ty được duyệt hoặc bị từ chối, tin bị admin khoá.
- **Gửi email:** theo cài đặt thông báo của từng người (bảng `notification_preferences` đã có trong identity). Hạ tầng gửi mail dùng lại mailer hiện có.
- **Thông báo tức thời (tuỳ chọn):** đẩy qua SSE/WebSocket, hoặc đơn giản là FE hỏi lại định kỳ số chưa đọc.

**Cần làm ở backend**
- Service riêng hoặc module trong identity: bảng `notifications`, API `/api/notifications` (liệt kê, đánh dấu đã đọc, đếm chưa đọc).
- Các service khác gửi sự kiện qua OpenFeign hoặc một hàng đợi tin nhắn.

### Việc nhỏ lẻ

- **Ảnh đại diện** (C14, identity-service): upload, cắt ảnh, lưu và trả URL trong `/me`.
- **Trang Người dùng (AD03, identity-service):**
  - lọc theo vai trò (API `GET /api/admin/users` chưa có tham số `role`);
  - cột công ty;
  - cột lần đăng nhập gần nhất (cần lưu `last_login_at`).
- **Hiệu năng** (recruitment-service): một số màn như Tổng quan ứng viên, trang tìm việc P02 lọc/sắp xếp đang lấy tối đa 100 bản ghi rồi tự tính ở FE. Nên chuyển sang lọc và đếm ở backend.
- **Đăng ký** (identity-service): form đăng ký trên canvas có trường "Họ và tên" mà `POST /api/auth/register` chưa nhận.

---

## Thứ tự đề xuất

**Task AI (M1–M3):**

1. **P0, cần cho demo:** F2-03, F3-01.
2. **P1, luồng tuyển dụng đầy đủ:** F3-04 → F3-05 → F2-08 (lời mời → kết quả về đơn → xếp hạng kết hợp). Song song: F3-03, F2-04, F1-04.
3. **P1, trải nghiệm và hiệu năng:** F1-01, F3-02, F2-01, F1-02.
4. **Số liệu cho báo cáo:** F2-02, F3-08 (cùng đánh giá M1 đã có trong `extraction/eval`).
5. **P2:** các chức năng *Mới* còn lại, chỉ làm khi đã xong P0–P1.

Phụ thuộc chính: F3-04 và F3-05 cần RabbitMQ (INF) và AP-06 (đổi trạng thái đơn — đã có lõi #3); F2-07 cần notification-service (NT-00, NT-01); F2-05 cần CV-09.

**Tính năng nhóm Chung còn lại:**

1. `2 Thành viên công ty & lời mời` → `5 Module thông báo` (cần cho job alert F2-07, lời mời phỏng vấn F3-04 và thông báo khoá tin #13) → mẫu CV của `14` → `Việc nhỏ lẻ`.

## Phụ thuộc giữa module

| Module | Làm chính | Cần từ nhóm khác |
|---|---|---|
| **M1** | 8 Nhiều CV; F1-01 → F1-06 | Mẫu CV (14, nhóm Chung) cho F1-04 |
| **M2** | 7 Job alert, 9 Tìm CV; F2-01 → F2-08 | Thông báo (5), gỡ index AI khi đóng tin (4 / F2-04) |
| **M3** | 10 Mời phỏng vấn, 14 Ngân hàng câu hỏi, 15 Bổ sung phiên; F3-01 → F3-09 | Thành viên công ty (2) cho F3-09, thông báo (5) |
| **Chung** | 2 Thành viên, 5 Thông báo, mẫu CV (14), việc nhỏ lẻ | Điểm matching (F2-03) cho R06, kết quả phỏng vấn (F3-05) cho đơn |
| **frontend** | Nối API thật cho các phần mock còn lại (`#2`, `#5`, `#7`, `#8`, `#9`, `#10`, `#14`) | Các backend tương ứng |
