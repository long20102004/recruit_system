# M3-CLS-BE — Đối sánh, xem chi tiết việc, ứng tuyển

## Vai trò và luồng gọi

Các đường dẫn Java dưới đây nằm dưới `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/`. Bảng cũng là truy vết các phần tử; package View là nhóm trình bày trống, không phải lớp server thực sự.

| Phần tử | Vai trò và nguồn |
|---|---|
| `CvController` | Boundary nhận GET CV, gọi `CvService.mine`: `controller/CvController.java:17`. |
| `CvService` | Lấy hồ sơ và tạo form có cờ `analyzed`: `service/CvService.java:47`, `:123`. |
| `MatchingController` | Nhận yêu cầu điểm đã lưu và làm mới: `controller/MatchingController.java:17`, `:22`. |
| `MatchingService` | Kiểm tra ứng viên/CV; duyệt việc PUBLISHED, chuẩn bị profile/JD, gọi matching, lưu và sắp xếp: `service/MatchingService.java:35`, `:48`, `:75`, `:125`, `:135`. |
| `JobsController` | Nhận yêu cầu danh sách và chi tiết: `controller/JobsController.java:18`, `:34`. |
| `JobService` | Tìm việc, dựng response và kỹ năng: `service/JobService.java:33`, `:44`, `:116`. |
| `ApplicationsController` | Nhận yêu cầu ứng tuyển: `controller/ApplicationsController.java:17`. |
| `ApplicationService` | Kiểm tra vai trò, hồ sơ, trạng thái tin, đơn trùng; tạo và lưu đơn: `service/ApplicationService.java:26`. |
| `CvMatchingModule` | Đóng gói request tới `/match/no-llm`, kiểm tra hình dạng và miền giá trị kết quả: `service/matching/CvMatchingModule.java:17`. |
| `AiJsonClient` | Gửi JSON HTTP và ánh xạ lỗi dịch vụ AI: `client/AiJsonClient.java:15`. |
| `JobRepository` | Truy vấn việc theo điều kiện; `findById` kế thừa Spring Data: `repository/JobRepository.java:11`, `:23`; lời gọi `service/JobService.java:45`. |
| `JobSkillRepository` | Lấy kỹ năng tin: `repository/JobSkillRepository.java:10`, `:12`. |
| `MatchingResultRepository` | Truy vấn điểm đã lưu, tìm kết quả theo job/ứng viên/model để cập nhật: `repository/MatchingResultRepository.java:11`, `:21`, `:33`; `save` kế thừa. |
| `JobApplicationRepository` | Kiểm tra trùng, lưu đơn bằng `save` kế thừa: `repository/JobApplicationRepository.java:11`, `:13`, `service/ApplicationService.java:44`. |
| `CvDataRepository` | Đọc trường CV theo ứng viên và tên trường: `repository/CvDataRepository.java:8`, `:11`. |
| `Job` | Tin việc và các thuộc tính được đọc khi dựng kết quả: `entity/Job.java:18`. |
| `JobApplication` | Đơn ứng tuyển, tham chiếu job: `entity/JobApplication.java:17`, `:27`. |
| `MatchingResult` | Điểm, giải thích và tham chiếu job: `entity/MatchingResult.java:19`, `:32`. |

Luồng chính: `CvController.mine` → `CvService.mine` để frontend kiểm tra CV; `JobsController.list`/`get` → `JobService` → repository để lấy danh sách/chi tiết; `MatchingController.myMatches`/`refreshMine` → `MatchingService` → repository và `CvMatchingModule.match` → `AiJsonClient.post`; `ApplicationsController.apply` → `ApplicationService.apply` → kiểm tra/lưu qua repository. `refreshMine` gọi `runMatching` tuần tự cho mỗi job; không có giả định gọi song song. Các association Job có bội số theo `@ManyToOne(optional = false)`; các dependency biểu diễn lời gọi hoặc kiểu repository, không suy diễn sở hữu vòng đời.

Để không vượt 18 lớp/interface, hình lược bớt `CandidateProfileRepository` (được gọi tại `service/MatchingService.java:229`, `service/ApplicationService.java:83`), `IdentityClient` (dựng response tại `service/MatchingService.java:176`, `service/ApplicationService.java:73`), `SettingService` (CV form tại `service/CvService.java:125`), thực thể CV/hồ sơ/kỹ năng và các DTO. Đây là các phụ thuộc có thật, không phải nói rằng chúng không tồn tại. Các lớp response xuất hiện trong kiểu trả về, nhưng không có phần tử DTO riêng; View backend để trống vì không có server-rendered view trong lát cắt này. Chỉ chọn thuộc tính/phương thức liên quan, không liệt kê toàn bộ lớp; phương thức Spring Data kế thừa như `save`, `findById` không khai báo lại như thể source repository tự định nghĩa chúng.

## Pattern thực sự có

- **Repository / Spring Data:** `JobRepository`, `MatchingResultRepository`, `JobApplicationRepository`, `JobSkillRepository`, `CvDataRepository` là interface `JpaRepository` (`repository/JobRepository.java:11`, `repository/MatchingResultRepository.java:11`, `repository/JobApplicationRepository.java:11`, `repository/JobSkillRepository.java:10`, `repository/CvDataRepository.java:8`); các service gọi chúng. Giúp nghiệp vụ tìm việc, lưu điểm và kiểm tra đơn trùng không phải tự viết lớp thao tác SQL; truy vấn đặc thù vẫn nằm trong repository.
- **DTO:** các record `CvDtos.CvFormResponse`, `JobDtos.JobResponse`, `MatchingDtos.MatchResponse`, `ApplicationDtos.ApplyRequest`/`ApplicationResponse` khai báo tại `dto/CvDtos.java:13`, `dto/JobDtos.java:18`, `dto/MatchingDtos.java:12`, `dto/ApplicationDtos.java:12`, `:15`. Service dựng response ở `service/JobService.java:132`, `service/MatchingService.java:170`, `service/ApplicationService.java:67`. Giúp frontend nhận dữ liệu hiển thị đã tổng hợp thay vì phơi trực tiếp entity JPA và phụ thuộc lazy.
- **Constructor Dependency Injection:** `@RequiredArgsConstructor` và các trường `final` tại `controller/MatchingController.java:12`, `:15`, `service/MatchingService.java:18`, `:26`; `CvMatchingModule` có constructor rõ ràng tại `service/matching/CvMatchingModule.java:14`. Spring cung cấp phụ thuộc; có thể thay repository/client bằng test double khi kiểm thử mà không phải gọi CSDL hoặc AI thật.

## Mâu thuẫn và giới hạn

- `source/recruit_system/docs/Module3_Interview_Flow.md:1` gọi Module 3 là luồng phỏng vấn; M3 của task là đối sánh/xem việc/ứng tuyển. Không đưa lớp phỏng vấn vào hình.
- Trang chi tiết không có nút ứng tuyển; nút nằm tại trang chủ (`source/recruit_system/frontend/src/pages/candidate/CandidateJobDetailPage.tsx:153`, `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:211`). Không mô tả một route ứng tuyển trực tiếp từ trang chi tiết.
- PDF báo cáo không có trên đĩa, không thể đối chiếu trực tiếp. `docs/schema.dbml` là lược đồ, không chứng minh luồng lớp này; không suy diễn mâu thuẫn chưa kiểm chứng.

## Cần xác nhận

- Có dự định bổ sung nút ứng tuyển tại trang chi tiết việc hay giữ thao tác ứng tuyển tại trang chủ?
