# Kế hoạch chức năng hệ thống HireLens

Ngày lập: 24/11/2026. Nguồn: đọc code `backend/`, `frontend/src/`, `services/`, `AI/`, `infra/gateway/`, `docker-compose.yml` và đối chiếu với báo cáo mẫu `docs/reports/template.pdf` (chương 2–4).

Ký hiệu trạng thái: ✅ đã có (BE + FE) · 🟡 có một phần · ❌ chưa có.
Ưu tiên: **P0** cần cho luồng tuyển dụng tối thiểu · **P1** nên có để khớp báo cáo · **P2** bổ sung nếu còn thời gian.
Khối lượng ước lượng: S (≤1 ngày) · M (2–3 ngày) · L (≥4 ngày).

---

## 1. Ba module (microservice) hiện tại

| Module | Cổng | Database | Phạm vi hiện tại |
|---|---|---|---|
| **identity-service** | 8081 | identity-db | Tài khoản, đăng nhập JWT, chọn vai trò; API nội bộ `/internal/users/{id}` |
| **recruitment-service** | 8082 | recruitment-db | CV (upload + AI trích xuất), việc làm, ứng tuyển, matching CV–JD, dashboard nhà tuyển dụng, công ty (tự sinh) |
| **interview-service** | 8083 | interview-db | Ngân hàng câu hỏi, phiên luyện phỏng vấn, chấm điểm AI, lịch sử, tổng kết |
| **notification-service** *(mới, đề xuất)* | 8084 | notification-db | Thông báo trong app, email, job alert; nhận sự kiện từ các service khác qua message broker |

Thành phần đi kèm (không tính là module nghiệp vụ):

| Thành phần | Vai trò | Module gọi |
|---|---|---|
| `backend/common` | Security, JWT, service token, `RemotePrincipalLookup`, Feign client gọi giữa service (`IdentityServiceClient`, `RecruitmentServiceClient`, `InterviewServiceClient`) | Cả 3 |
| `infra/gateway` (Nginx :8080) | Định tuyến `/api/auth` → identity; `/api/jobs\|cvs\|applications\|matching\|dashboard` → recruitment; `/api/interviews` → interview | — |
| `services/cv-extraction-ai` | Trích xuất CV (Qwen3-1.7B LoRA) — AI Module 1 | recruitment |
| `services/cv-matching-ai` | Đối sánh CV–JD (`/match/no-llm`) — AI Module 2 | recruitment |
| `AI/` | Chấm câu trả lời phỏng vấn (BERTScore + rubric) — AI Module 3 | interview |
| `ai-service/`, `ai/cvmatch` | Bản cũ / mã nghiên cứu, không deploy | — |

## 2. Đánh giá: thiết kế 3 microservice đã đáp ứng chưa?

**Kết luận:** 3 service hiện tại đủ cho luồng tuyển dụng chính (đăng tin → ứng tuyển → xử lý đơn → phỏng vấn). Để đạt mức tương tự ITviec (thông báo, email, job alert), **thêm notification-service** và một message broker; các chức năng khác vẫn nằm trong 3 module cũ. Cần chỉnh thêm một số điểm sau.

Điểm đã hợp lý:
- Mỗi service có database riêng. Các service gọi nhau qua REST nội bộ có service token, và gateway chặn `/internal/*` từ bên ngoài.
- Ranh giới nghiệp vụ rõ: danh tính / tuyển dụng / phỏng vấn. Phần AI tách thành service Python riêng.

Điểm cần lưu ý khi mở rộng:
1. **recruitment-service sẽ phình to.** Các phần Company, thành viên công ty, Job, CV, Application, Matching, Gợi ý việc làm, Saved job/CV và Notification đều thuộc service này. Đề xuất chia package rõ ràng theo `company / job / cv / application / matching / recommend / notification` để mỗi thành viên làm một package, tránh sửa cùng file.
2. **Không có Notification service hay message broker.** Để hệ thống tiến gần ITviec (thông báo trong app, email, job alert), tách **notification-service** thành service thứ 4. Đây là chức năng xuyên suốt: mọi service đều phát sự kiện, và việc gửi email hay tính job alert phải chạy bất đồng bộ, không được làm chậm luồng chính. Cách giao tiếp xem mục 2.1.
3. **Công ty đang là placeholder.** `ProfileProvisioningService` tự tạo công ty "`<Tên> #<id>`" cho mỗi recruiter. Cần thay bằng luồng đăng ký công ty và admin duyệt.
4. **Admin đặt ở module sở hữu dữ liệu:** quản lý user ở identity; duyệt công ty và khóa tin ở recruitment; quản lý ngân hàng câu hỏi ở interview. Frontend gom lại thành một khu `/admin`.
5. **Mỗi request đã xác thực đều gọi identity** (`RemotePrincipalLookup`). Cách này chấp nhận được ở quy mô đồ án. Nếu cần tối ưu thì cache ngắn hạn (P2).
6. **Trạng thái lệch so với báo cáo mẫu.** Giữ enum hiện tại và chỉ bổ sung trạng thái còn thiếu, để không phá dữ liệu và frontend:
   - Application: hiện có `SUBMITTED, REVIEWING, INTERVIEW, REJECTED, HIRED`. Thêm `WITHDRAWN` (ứng viên rút đơn).
   - Job: hiện có `DRAFT, PUBLISHED, CLOSED`. Thêm `EXPIRED` (tự chuyển khi quá `deadline`) và `LOCKED` (admin khóa).
   - Company: chưa có trạng thái. Thêm `PENDING, ACTIVE, REJECTED, LOCKED`.
   - Mọi thay đổi schema làm bằng **migration Flyway mới**; không sửa migration đã chạy.
7. **Công nghệ khác báo cáo mẫu.** Mẫu dùng Node/Prisma/PostgreSQL/Firebase/FAISS; dự án dùng Spring Boot, MySQL, lưu file trên ổ đĩa và AI matching riêng. Đây là khác biệt hợp lệ, chỉ cần mô tả đúng trong báo cáo.

### 2.1. Giao tiếp giữa các service: sync hay message broker?

**Hiện trạng:** toàn bộ là REST đồng bộ. Gọi giữa các service Java dùng Spring Cloud OpenFeign (client khai báo trong `backend/common/.../client`, kèm `SERVICE_TOKEN`); gọi sang service AI vẫn dùng client HTTP riêng của từng module.

**Quyết định đề xuất: kết hợp, không dùng 100% sync.** Quy tắc chọn:

| Loại tương tác | Cách giao tiếp | Lý do |
|---|---|---|
| **Truy vấn** cần câu trả lời ngay để xử lý tiếp | **Sync REST** (OpenFeign) | Bên gọi cần dữ liệu ngay mới đi tiếp được |
| **Sự kiện** "việc X đã xảy ra", bên phát không cần chờ kết quả | **Async qua message broker** | Gửi thông báo/email chậm hay lỗi cũng không làm hỏng giao dịch chính. Thêm bên nhận mới mà không phải sửa bên phát |

Áp dụng cụ thể:

| Tương tác | Từ → Đến | Cách |
|---|---|---|
| Lấy user theo id / email (xác thực, mời thành viên) | mọi service → identity | Sync |
| Lấy ngữ cảnh phỏng vấn (`/internal/interview-context`) | interview → recruitment | Sync |
| Kiểm tra công ty ACTIVE, quyền thành viên khi đăng tin | trong recruitment | Gọi nội bộ |
| Gọi AI (trích xuất CV, matching, chấm điểm) | recruitment / interview → AI | Sync, timeout dài |
| `ApplicationSubmitted`, `ApplicationStatusChanged` | recruitment → notification | **Async** |
| `CompanyRegistered`, `CompanyApproved`, `CompanyInvitationCreated` | recruitment → notification | **Async** |
| `JobPublished` (để tính job alert) | recruitment → notification | **Async** |
| `InterviewInvited`, `InterviewCompleted` | interview → notification | **Async** |
| `InterviewCompleted` (điểm tổng, link phiên) → lưu điểm phỏng vấn vào đơn ứng tuyển | interview → recruitment | **Async** |
| `ApplicationStatusChanged` → `INTERVIEW` → tự tạo lời mời phiên phỏng vấn | recruitment → interview | **Async** |
| `ApplicationWithdrawn`, `ApplicationStatusChanged` → `REJECTED`, `JobClosed` → hủy lời mời / phiên đang chờ | recruitment → interview | **Async** |
| `CompanyMemberRemoved` → cập nhật quyền xem kết quả (`recruiter_user_id`) | recruitment → interview | Async (P2) |
| `CvUpdated`, `JobUpdated` (tính lại gợi ý việc làm, RS-01) | recruitment → recruitment / worker | Async (P2), trước mắt dùng `@Scheduled` |
| `UserLocked` | identity → các service | Async (P2) |

**Chọn broker: RabbitMQ (khuyến nghị) hay Kafka?**

| Tiêu chí | RabbitMQ | Kafka |
|---|---|---|
| Mục đích chính | Hàng đợi tin nhắn / phân phối sự kiện | Event streaming, log sự kiện lưu lâu, đọc lại được |
| Tài nguyên khi chạy local | Nhẹ (~150 MB RAM), một container | Nặng hơn (~1 GB RAM), chế độ KRaft |
| Spring | `spring-boot-starter-amqp`, retry + dead-letter queue có sẵn | `spring-kafka`, phải tự lo partition, consumer group, offset |
| Lượng sự kiện của hệ thống | Vài chục đến vài nghìn sự kiện/ngày, rất phù hợp | Thừa năng lực |
| Đọc lại sự kiện cũ, nhiều hệ thống phân tích cùng đọc | Không mạnh | Điểm mạnh |
| Giá trị trình bày trong báo cáo | Đủ để minh họa kiến trúc hướng sự kiện | "Nghe lớn" hơn nhưng khó giải thích vì sao cần |

Một sự kiện có thể có nhiều bên nhận: `ApplicationStatusChanged` đi tới cả notification lẫn interview. Mỗi service nhận có queue riêng gắn vào cùng exchange, nên bên phát không cần biết có những bên nhận nào.

**Xử lý nền cho lời gọi AI (không bắt buộc dùng broker).** Chấm câu trả lời phỏng vấn và trích xuất CV hiện gọi AI sync, timeout tới 180 giây. Nên chuyển sang: API trả về ngay với trạng thái `PENDING`, xử lý bằng `@Async` hoặc worker, frontend poll kết quả. Enum CV `PENDING/PROCESSING/COMPLETED/FAILED` đã có sẵn. Nếu sau này cần nhiều worker thì đưa job vào RabbitMQ (task INF-06, INF-07).

→ **Khuyến nghị RabbitMQ** (topic exchange `hirelens.events`, mỗi service nhận có một queue riêng kèm dead-letter queue). Chỉ chọn Kafka khi đề tài có yêu cầu streaming hoặc phân tích sự kiện, hoặc nhóm chủ động muốn học Kafka.

**Nếu muốn 100% sync (OpenFeign):** vẫn làm được. Khi đó recruitment gọi `POST /internal/notifications` của notification-service sau mỗi sự kiện. Nhược điểm:
- notification-service chết thì ứng tuyển / đổi trạng thái lỗi theo, hoặc phải tự viết try-catch và bỏ qua thông báo.
- Mỗi lần thêm bên nhận mới phải sửa code bên phát.
- Job alert vẫn cần chạy theo lịch.

Phương án này chỉ chấp nhận được nếu nhóm thiếu thời gian.

**Quy ước khi dùng broker:**
- Publish **sau khi transaction commit** (`@TransactionalEventListener(phase = AFTER_COMMIT)`), để không phát sự kiện cho dữ liệu đã bị rollback. Outbox table là P2.
- Bên nhận phải **idempotent**: mỗi sự kiện mang `eventId`, notification-service lưu `eventId` đã xử lý để bỏ qua bản trùng.
- Định dạng sự kiện chung đặt ở `backend/common` (`event/` package): `eventId`, `type`, `occurredAt`, `actorId`, `payload`.
- Về OpenFeign: đã chuyển các lời gọi giữa service Java sang Feign (INF-04). Client gọi AI (`AiJsonClient`, `HttpCvMatchClient`, `AiScoringClient`) giữ nguyên.

## 3. Danh sách chức năng chi tiết

### 3.1. identity-service

| ID | Chức năng | Actor | Trạng thái | Việc cần làm | Ưu tiên | KL |
|---|---|---|---|---|---|---|
| ID-01 | Đăng ký tài khoản | Khách | ✅ | — | — | — |
| ID-02 | Đăng nhập (JWT) | Tất cả | ✅ | — | — | — |
| ID-03 | Lấy thông tin bản thân `/auth/me` | Tất cả | ✅ | — | — | — |
| ID-04 | Chọn vai trò Ứng viên / Nhà tuyển dụng (1 lần) | User mới | ✅ | — | — | — |
| ID-05 | Đăng xuất | Tất cả | 🟡 | FE xóa token là đủ; nếu cần thu hồi token thì thêm blacklist (P2) | P1 | S |
| ID-06 | Cập nhật hồ sơ cá nhân (họ tên, SĐT, giới tính, ngày sinh, avatar) | Tất cả | ❌ | BE: `PUT /api/auth/me` + migration thêm cột. FE: trang Hồ sơ | P1 | M |
| ID-07 | Đổi mật khẩu | Tất cả | ❌ | BE: `POST /api/auth/password` (kiểm mật khẩu cũ). FE: form | P1 | S |
| ID-08 | Quên / đặt lại mật khẩu qua email | Tất cả | ❌ | Cần SMTP + token reset | P2 | M |
| ID-09 | Refresh token | Tất cả | ❌ | Tùy chọn | P2 | M |
| ID-10 | Admin: danh sách người dùng (lọc, phân trang) | Admin | ❌ | BE: `GET /api/admin/users`. FE: trang admin | P1 | M |
| ID-11 | Admin: khóa / mở khóa người dùng | Admin | 🟡 | Enum `BANNED/INACTIVE` đã có nhưng chưa có API. Chặn đăng nhập khi bị khóa | P1 | S |
| ID-12 | Admin: đổi vai trò người dùng | Admin | ❌ | BE + FE | P2 | S |
| ID-13 | Ghi `last_login_at` | — | ❌ | Migration + cập nhật khi login | P2 | S |

### 3.2. recruitment-service

#### a) Công ty và thành viên

| ID | Chức năng | Actor | Trạng thái | Việc cần làm | Ưu tiên | KL |
|---|---|---|---|---|---|---|
| RC-01 | Đăng ký công ty (tên, MST, lĩnh vực, quy mô, website, địa chỉ, mô tả, file giấy phép) → PENDING | Recruiter | ❌ | Migration thêm cột và `status` cho `companies`. API `POST /api/companies`. Bỏ cơ chế tự sinh công ty. FE: trang đăng ký công ty | P0 | L |
| RC-02 | Xem / sửa thông tin công ty, logo | Owner/Manager | ❌ | `GET/PUT /api/companies/mine`, upload logo | P1 | M |
| RC-03 | Trang công ty công khai (thông tin + việc đang tuyển) | Khách/Ứng viên | ❌ | `GET /api/companies/{id}`. FE trang công ty | P1 | M |
| RC-04 | Tìm kiếm công ty | Khách/Ứng viên | ❌ | `GET /api/companies?keyword=&city=&industry=` | P2 | S |
| RC-05 | Admin duyệt / từ chối công ty (kèm lý do) | Admin | ❌ | `PATCH /api/admin/companies/{id}/status`. FE màn kiểm duyệt | P0 | M |
| RC-06 | Admin khóa / mở khóa công ty | Admin | ❌ | Như RC-05 | P1 | S |
| RC-07 | Mời thành viên (email + vai trò), lời mời hết hạn sau 7 ngày | Owner/Manager | ❌ | Bảng `company_invitations`; thêm cột vai trò `OWNER/MANAGER/RECRUITER/VIEWER` vào `recruiter_profiles`. Tra email qua identity (cần thêm endpoint nội bộ tra theo email) | P1 | L |
| RC-08 | Chấp nhận / từ chối lời mời | User | ❌ | API + FE danh sách lời mời | P1 | M |
| RC-09 | Danh sách thành viên, đổi vai trò, xóa thành viên | Owner/Manager | ❌ | API + FE | P1 | M |
| RC-10 | Phân quyền theo vai trò công ty khi đăng tin / xử lý đơn | — | 🟡 | Hiện chỉ kiểm tra "tin của mình". Đổi thành "tin thuộc công ty của mình + vai trò đủ quyền" | P1 | M |

#### b) Việc làm (Job)

| ID | Chức năng | Actor | Trạng thái | Việc cần làm | Ưu tiên | KL |
|---|---|---|---|---|---|---|
| JB-01 | Danh sách việc làm công khai, lọc keyword / thành phố | Khách | ✅ | — | — | — |
| JB-02 | Chi tiết việc làm | Khách | ✅ | — | — | — |
| JB-03 | Tạo tin tuyển dụng (lưu nháp / đăng ngay) | Recruiter | 🟡 | Đã có tạo tin. Cần thêm nút "Lưu nháp" / "Đăng ngay" và validate deadline ≥ hôm nay. Chỉ công ty ACTIVE mới được đăng | P0 | S |
| JB-04 | Sửa tin tuyển dụng | Recruiter | ❌ | `PUT /api/jobs/{id}` + FE form sửa | P0 | M |
| JB-05 | Đóng / mở lại / đăng tin nháp (đổi trạng thái) | Recruiter | 🟡 | BE `PATCH /jobs/{id}/status` đã có, FE chưa gọi. Thêm nút trên `RecruiterJobsPage` | P0 | S |
| JB-06 | Tự hết hạn tin khi quá deadline (`EXPIRED`) | Hệ thống | ❌ | Job `@Scheduled` hoặc lọc khi truy vấn | P1 | S |
| JB-07 | Phân trang, sắp xếp; lọc theo lương, kinh nghiệm, loại hình, kỹ năng, ngành | Khách | 🟡 | API hiện trả `List`, chưa phân trang. Bổ sung `Pageable` + filter. FE: bộ lọc + phân trang | P1 | M |
| JB-08 | Hiển thị số lượng ứng viên của tin | Recruiter | 🟡 | Kiểm tra dashboard; thêm cột `applicationCount` trên bảng tin | P2 | S |
| JB-09 | Việc làm tương tự (trang chi tiết) | Ứng viên | ❌ | Dùng embedding / skill overlap; có thể dùng chung với RS-02 | P2 | M |
| JB-10 | Admin: danh sách tin, khóa / mở khóa tin | Admin | ❌ | `GET /api/admin/jobs`, `PATCH .../lock` | P1 | M |

#### c) CV ứng viên

| ID | Chức năng | Actor | Trạng thái | Việc cần làm | Ưu tiên | KL |
|---|---|---|---|---|---|---|
| CV-01 | Upload CV PDF → AI trích xuất → ứng viên chỉnh sửa → lưu | Ứng viên | ✅ | — (AI Module 1) | — | — |
| CV-02 | Xem CV hiện tại | Ứng viên | ✅ | — | — | — |
| CV-03 | Tạo CV từ form (không upload) | Ứng viên | 🟡 | Form chỉnh sửa đã có. Cần cho phép nhập từ đầu khi chưa có file | P1 | S |
| CV-04 | Nhiều CV (tối đa 5), đặt CV chính | Ứng viên | ❌ | Hiện mỗi ứng viên 1 CV. Cần `GET/POST/DELETE /api/cvs/{id}`, cột `is_main`; FE dạng danh sách thẻ | P1 | L |
| CV-05 | Xóa CV | Ứng viên | ❌ | Đi kèm CV-04 | P1 | S |
| CV-06 | Tải CV (file gốc) | Ứng viên/Recruiter | ❌ | `GET /api/cvs/{id}/file` (kiểm quyền: chủ CV hoặc recruiter có đơn ứng tuyển kèm CV đó) | P0 | S |
| CV-07 | Xuất CV PDF theo mẫu | Ứng viên | ❌ | Render HTML → PDF ở backend | P2 | L |
| CV-08 | Admin quản lý mẫu CV (CRUD) | Admin | ❌ | Chỉ làm nếu làm CV-07 | P2 | M |
| CV-09 | Bật / tắt "đang tìm việc" (cho phép recruiter tìm CV) | Ứng viên | ❌ | Cột `is_open_for_job` | P2 | S |

#### d) Ứng tuyển (Application)

| ID | Chức năng | Actor | Trạng thái | Việc cần làm | Ưu tiên | KL |
|---|---|---|---|---|---|---|
| AP-01 | Nộp đơn ứng tuyển (chặn trùng, chỉ tin PUBLISHED) | Ứng viên | ✅ | Bổ sung modal chọn CV + thư giới thiệu (cover letter) khi có CV-04 | P1 | S |
| AP-02 | Danh sách đơn đã nộp + trạng thái | Ứng viên | 🟡 | BE `GET /applications/mine` đã có. Cần trang FE "Đơn ứng tuyển của tôi" có lọc theo trạng thái | P0 | M |
| AP-03 | Rút đơn (`WITHDRAWN`) | Ứng viên | ❌ | `PATCH /api/applications/{id}/withdraw` + migration enum | P1 | S |
| AP-04 | Danh sách đơn theo tin (lọc, tìm, sắp xếp) | Recruiter | 🟡 | Đã có danh sách. Thêm lọc theo tin / trạng thái, tìm kiếm, phân trang | P0 | M |
| AP-05 | Xem chi tiết đơn: CV, cover letter, điểm matching, kết quả phỏng vấn | Recruiter | 🟡 | Có liên kết rời rạc. Cần trang hoặc drawer chi tiết gộp | P0 | M |
| AP-06 | **Đổi trạng thái đơn** (SUBMITTED → REVIEWING → INTERVIEW → HIRED / REJECTED) | Recruiter | ❌ | **Lỗ hổng lớn nhất của luồng tuyển dụng.** `PATCH /api/applications/{id}/status`, kiểm chuyển trạng thái hợp lệ, lưu lịch sử. FE nút Duyệt / Từ chối | P0 | M |
| AP-07 | Ghi chú, đánh giá ứng viên | Recruiter | ❌ | Cột `notes`, `rating` | P2 | S |
| AP-08 | Lịch sử đổi trạng thái đơn | — | ❌ | Bảng `application_status_history` (đi cùng AP-06) | P1 | S |

#### e) Matching và gợi ý việc làm (AI Module 2)

| ID | Chức năng | Actor | Trạng thái | Việc cần làm | Ưu tiên | KL |
|---|---|---|---|---|---|---|
| MT-01 | Ứng viên xem việc phù hợp với CV + làm mới | Ứng viên | ✅ | — | — | — |
| MT-02 | Recruiter chạy matching cho ứng viên của một tin, xếp hạng | Recruiter | ✅ | — | — | — |
| MT-03 | Chi tiết điểm matching trên trang việc làm | Ứng viên | ✅ | — | — | — |
| RS-01 | Gợi ý việc làm tự động, tính trước (batch theo lịch, chỉ tính lại khi CV/Job đổi — content hash) | Hệ thống | 🟡 | Hiện chỉ tính khi bấm làm mới, chấm 1 CV với từng job (O(n)). Thêm `@Scheduled` + bảng kết quả, và dùng `/match_batch` nếu phù hợp. **Đề xuất theo sự kiện** (cvmatch đã có API, 26/11): `JobPublished` → `POST /match/jd/{id}` với `only_recommendable`, `min_score`, `exclude_cv_ids`; `CvUpdated` → `POST /match/cv/{id}`; đồng bộ cờ bằng `PATCH /cv/{id}` `{recommendable}`. Xem `ai-service/matching/service/docs/plan/S07 Gợi ý theo sự kiện - phía cvmatch.md` | P1 | L |
| RS-02 | Đánh giá chất lượng gợi ý (MRR, NDCG@K, HitRate@K) cho báo cáo chương 3 | — | ❌ | Script đánh giá trong `ai/cvmatch` | P1 | M |
| RS-03 | Recruiter tìm kiếm CV ứng viên (đang mở tìm việc) | Recruiter | ❌ | `GET /api/cvs/search`; cần CV-09 | P2 | M |

#### f) Lưu, dashboard, phát sự kiện

| ID | Chức năng | Actor | Trạng thái | Việc cần làm | Ưu tiên | KL |
|---|---|---|---|---|---|---|
| SV-01 | Lưu / bỏ lưu việc làm, danh sách việc đã lưu | Ứng viên | ❌ | Bảng `saved_jobs` + API + FE nút ♥ | P1 | M |
| SV-02 | Lưu CV ứng viên kèm ghi chú | Recruiter | ❌ | Bảng `saved_cvs` | P2 | M |
| EV-01 | Phát sự kiện ứng tuyển, công ty và việc làm lên broker (xem bảng ở mục 2.1) | Hệ thống | ❌ | Publisher dùng chung + gọi publish tại AP-01, AP-03, AP-06, RC-01, RC-05, RC-07, JB-03/JB-05. Mỗi nhóm tự gắn vào chức năng mình làm | P1 | M |
| EV-02 | Nhận `InterviewCompleted` → lưu điểm và link phiên vào đơn ứng tuyển; AP-05 và dashboard đọc trực tiếp, sắp xếp ứng viên theo điểm phỏng vấn | Hệ thống | ❌ | Consumer + migration thêm cột `interview_score`, `interview_session_id` vào `job_applications`; chống trùng bằng `eventId` | P1 | M |
| DB-01 | Dashboard recruiter (thống kê) | Recruiter | ✅ | — | — | — |
| DB-02 | Dashboard admin (số công ty, tin, người dùng, công ty chờ duyệt) | Admin | ❌ | BE gom số liệu (gọi identity lấy số user). FE `/admin` | P1 | M |

### 3.3. interview-service (AI Module 3)

| ID | Chức năng | Actor | Trạng thái | Việc cần làm | Ưu tiên | KL |
|---|---|---|---|---|---|---|
| IV-01 | Tạo phiên luyện phỏng vấn theo JD/CV (chọn câu theo kỹ năng, cấp độ) | Ứng viên | ✅ | — | — | — |
| IV-02 | Trả lời và chấm điểm AI (BERTScore + rubric, ý đúng / ý thiếu) | Ứng viên | ✅ | — | — | — |
| IV-03 | Lịch sử phiên, tổng kết phiên | Ứng viên | ✅ | — | — | — |
| IV-04 | Xem ngân hàng câu hỏi | Recruiter | ✅ | — | — | — |
| IV-05 | Recruiter xem kết quả phỏng vấn của ứng viên ứng tuyển tin của mình | Recruiter | 🟡 | BE đã cho phép (`recruiter_user_id`). Thiếu API liệt kê phiên theo tin / ứng viên và panel "Phiên gần nhất" trên `RecruiterInterviewsPage` | P0 | M |
| IV-06 | Lời mời phỏng vấn cho một đơn: nhận `ApplicationStatusChanged` → `INTERVIEW` từ RabbitMQ rồi tự tạo lời mời phiên; ứng viên thấy lời mời và bắt đầu phiên từ đó | Recruiter → Ứng viên | ❌ | Consumer + bảng `interview_invitations` (application_id, candidate_id, job_id, recruiter_user_id, status, expires_at) + API danh sách lời mời của ứng viên; phát `InterviewInvited` | P1 | M |
| IV-10 | Hủy lời mời / phiên đang chờ khi đơn bị rút, bị từ chối hoặc tin bị đóng | Hệ thống | ❌ | Consumer `ApplicationWithdrawn`, `ApplicationStatusChanged` → `REJECTED`, `JobClosed` | P1 | S |
| IV-11 | Phát `InterviewCompleted` khi phiên hoàn thành (kèm điểm tổng, application_id nếu có) | Hệ thống | ❌ | Gắn vào luồng hoàn thành phiên hiện có | P1 | S |
| IV-12 | Cập nhật quyền xem kết quả khi recruiter rời công ty | Hệ thống | ❌ | Consumer `CompanyMemberRemoved` | P2 | S |
| IV-07 | CRUD câu hỏi và rubric | Admin (và Recruiter cho câu riêng của công ty, tùy chọn) | ❌ | API + FE quản lý; câu mới đặt `review_status` | P1 | M |
| IV-08 | Bộ câu hỏi cấp Senior | — | ❌ | Bổ sung dữ liệu bằng migration mới | P2 | M |
| IV-09 | Đánh giá chất lượng chấm điểm với đáp án do người chấm | — | ❌ | Hiện chỉ có nhãn tổng hợp | P2 | M |

### 3.4. notification-service (mới)

| ID | Chức năng | Actor | Trạng thái | Việc cần làm | Ưu tiên | KL |
|---|---|---|---|---|---|---|
| NT-00 | Khởi tạo service: Spring Boot, `notification-db`, Flyway, dùng `backend/common` cho JWT; thêm vào `docker-compose.yml` và route gateway `/api/notifications` | — | ❌ | Theo khung của interview-service | P1 | M |
| NT-01 | Nhận sự kiện từ broker → tạo thông báo trong app: đơn mới (→ recruiter), đổi trạng thái đơn (→ ứng viên), công ty đăng ký (→ admin), công ty được duyệt/từ chối (→ owner), lời mời công ty (→ người được mời), mời phỏng vấn (→ ứng viên) | Tất cả | ❌ | Consumer + bảng `notifications` (user_id, type, title, body, link, is_read, created_at) + bảng `processed_events` để chống trùng | P1 | L |
| NT-02 | API: danh sách thông báo (phân trang), số chưa đọc, đánh dấu đã đọc / đọc tất cả | Tất cả | ❌ | `GET /api/notifications`, `GET /api/notifications/unread-count`, `PATCH /api/notifications/{id}/read`, `PATCH /api/notifications/read-all`. FE: chuông thông báo, polling 30 giây (WebSocket là P2) | P1 | M |
| NT-03 | Gửi email theo sự kiện (mẫu HTML) | Hệ thống | ❌ | Spring Mail + SMTP. Dev dùng **Mailpit** trong docker-compose để xem mail | P2 | M |
| NT-04 | Cài đặt nhận thông báo (bật/tắt email theo loại) | Tất cả | ❌ | Bảng `notification_preferences` | P2 | S |
| NT-05 | **Job alert:** ứng viên đăng ký tiêu chí (từ khóa, kỹ năng, thành phố, mức lương); khi có `JobPublished` khớp thì gửi thông báo hoặc email (gửi ngay hoặc gom theo ngày) | Ứng viên | ❌ | Bảng `job_alerts`. Đối chiếu tiêu chí với payload sự kiện. FE: trang quản lý job alert | P2 | L |
| NT-06 | Hiển thị lời mời / thông báo realtime (WebSocket/SSE) | Tất cả | ❌ | Thay polling | P2 | M |

### 3.5. Hạ tầng dùng chung

| ID | Việc | Trạng thái | Ghi chú | Ưu tiên | KL |
|---|---|---|---|---|---|
| INF-01 | Thêm RabbitMQ vào `docker-compose.yml` (có management UI) | ❌ | Theo quyết định ở mục 2.1 | P1 | S |
| INF-02 | Thư viện sự kiện trong `backend/common`: `DomainEvent`, `EventPublisher` (publish AFTER_COMMIT), cấu hình exchange / queue / DLQ | ❌ | Làm **trước** EV-01 và NT-01 | P1 | M |
| INF-03 | Lưu file bằng MinIO thay cho ổ đĩa local (CV, logo, giấy phép kinh doanh) | ❌ | Tùy chọn | P2 | M |
| INF-04 | Chuyển `ServiceHttpClient` sang OpenFeign | ✅ | Đã làm cho gọi giữa service Java; client gọi AI chưa đổi | — | — |
| INF-05 | Đưa role/status vào JWT hoặc cache `RemotePrincipalLookup` để giảm gọi identity | ❌ | Quan trọng hơn khi có 4 service | P2 | S |
| INF-06 | Chấm câu trả lời phỏng vấn chạy nền: nộp câu trả lời → `PENDING` → `@Async` gọi AI → FE poll kết quả | ❌ | Thuộc interview-service; tránh request treo 180 giây | P2 | M |
| INF-07 | Trích xuất CV chạy nền: upload → `PROCESSING` → `@Async` gọi AI → FE poll `parsing_status` | ❌ | Thuộc recruitment-service; dùng enum CV đã có | P2 | M |
| INF-08 | Khai báo topology RabbitMQ: exchange `hirelens.events` (topic); queue `notification.events`, `interview.events`, `recruitment.events`, mỗi queue có DLQ; routing key theo tên sự kiện (`application.status-changed`, `interview.completed`, …) | ❌ | Làm cùng INF-02, ghi vào `backend/README.md` | P1 | S |

### 3.6. Frontend dùng chung / phi chức năng (phân cho người làm FE hoặc chia theo module)

| ID | Chức năng | Trạng thái | Ghi chú | Ưu tiên |
|---|---|---|---|---|
| FE-01 | Khu Admin `/admin` (layout, route guard riêng cho ADMIN) | ❌ | Hiện ADMIN bị đưa vào giao diện recruiter | P1 |
| FE-02 | Trang Hồ sơ cá nhân / đổi mật khẩu | ❌ | Đi với ID-06, ID-07 | P1 |
| FE-03 | Responsive mobile / tablet | 🟡 | Báo cáo mẫu có hình minh họa | P2 |
| FE-04 | Dọn mã chết: `data/mockData.ts`, `DemoBanner` | — | Không dùng nữa | P2 |
| NF-01 | Thời gian phản hồi ≤ 3 giây cho thao tác cơ bản (trừ AI) | Chưa đo | Đo bằng k6/JMeter cho báo cáo | P2 |
| NF-02 | Test tích hợp cho các API mới | — | Mỗi task tự viết test | P0 |

## 4. Gợi ý chia task cho thành viên

Chia theo module để mỗi người làm trên một service / package, hạn chế xung đột file:

| Nhóm | Module | Task chính (theo thứ tự) |
|---|---|---|
| A | recruitment – Application + Job | AP-06, AP-08, AP-04, AP-05, AP-02, AP-03, JB-03, JB-04, JB-05, JB-06, JB-07 |
| B | recruitment – Company + thành viên + Admin công ty / tin | RC-01, RC-05, RC-02, RC-10, RC-07, RC-08, RC-09, RC-06, JB-10, DB-02 |
| C | identity + FE Admin / Hồ sơ | ID-06, ID-07, ID-10, ID-11, FE-01, FE-02, ID-05 |
| D | recruitment – CV + Saved | CV-06, CV-03, CV-04, CV-05, AP-01, SV-01 |
| E | interview + Recommend (AI) | IV-05, IV-11, IV-06, IV-10, IV-07, RS-01, RS-02, INF-06 |
| F | notification-service + hạ tầng sự kiện | INF-01, INF-02, INF-08, NT-00, NT-01, NT-02, NT-03, NT-05 (và FE chuông thông báo) |

Task phát/nhận sự kiện trong recruitment do nhóm sở hữu chức năng tự làm: EV-01 chia cho A (AP-*, JB-*) và B (RC-*); EV-02 giao nhóm A; INF-07 giao nhóm D.

Thứ tự phụ thuộc cần lưu ý:
- RC-01 (công ty có trạng thái) phải xong trước RC-05, RC-07 và ràng buộc "công ty ACTIVE mới đăng tin" ở JB-03.
- AP-06 phải xong trước IV-06 (trạng thái INTERVIEW) và trước sự kiện `ApplicationStatusChanged`.
- Luồng phỏng vấn qua sự kiện: AP-06 (nhóm A) phát `ApplicationStatusChanged` → IV-06 / IV-10 (nhóm E) nhận; IV-11 (nhóm E) phát `InterviewCompleted` → EV-02 (nhóm A) nhận. Hai nhóm chốt payload của các sự kiện này trước khi code.
- Nhóm F làm INF-01, INF-02 và INF-08 **đầu tiên** và chốt danh sách sự kiện kèm payload (mục 2.1). Sau đó các nhóm A, B, E tự gọi `EventPublisher` trong chức năng mình làm (EV-01, IV-06). Notification-service có thể phát triển song song nhờ test bằng sự kiện giả.
- CV-04 (nhiều CV) đổi quan hệ CV ↔ ứng viên, nên ảnh hưởng matching và interview-context. Làm sau khi P0 ổn định và báo nhóm E.
- Nhiều nhóm cùng sửa recruitment-service: chốt trước số thứ tự migration Flyway (ví dụ nhóm A dùng V6x, B dùng V7x, D dùng V8x), hoặc đặt tên theo timestamp, để tránh trùng phiên bản.

## 5. Phần chưa xác minh

- Danh sách chức năng được lập bằng cách đọc code tĩnh, chưa chạy E2E toàn hệ thống.
- Một số trang FE chỉ đọc lướt, nên có thể còn nút chưa có handler chưa được liệt kê.
- Chưa xác minh `cv-matching-ai` có dùng `/match_batch` hay không.
- Sơ đồ trạng thái trong báo cáo mẫu là hình ảnh; các chuyển trạng thái ở mục 2 được suy ra từ phần mô tả và enum.
