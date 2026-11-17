# AN-M3 — Biểu đồ lớp pha phân tích chức năng đối sánh CV với việc làm, xem chi tiết việc, ứng tuyển

**Bước 1.** Từ các giao diện chính trong kịch bản và mã nguồn frontend, đề xuất ba lớp biên:

- `CandidateHomeView`: đại diện cho Trang chủ việc làm ứng viên (`CandidateHomePage.tsx:36`), cho phép tìm kiếm, lọc và duyệt danh sách việc làm, xem chi tiết tóm tắt việc được chọn và thực hiện nộp đơn ứng tuyển:
  - Thuộc tính ô nhập: `inKeyword`, `inCity`, `inMode`.
  - Thuộc tính dữ liệu hiển thị: `outJobList`, `outSelectedJob`, `outMatchScore`, `outBestMatch`.
  - Thuộc tính nút bấm/thao tác: `subSearch`, `subFilterMode`, `subViewMatching`, `subSelectJob`, `subApply`, `subReviewInterview`.
  - Nguồn: `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:36`.

- `CandidateMatchingView`: đại diện cho Trang việc làm phù hợp CV (`CandidateMatchingPage.tsx:21`), hiển thị bảng xếp hạng công việc theo độ phù hợp AI tính toán từ CV và cho phép kích hoạt làm mới điểm đối sánh:
  - Thuộc tính dữ liệu hiển thị: `outRankedMatches`, `outJobList`, `outScoreError`, `outCvStatusNote`.
  - Thuộc tính nút bấm/thao tác: `subRematch`, `subUploadCv`.
  - Thuộc tính danh sách bấm được: `outsubJobDetail` (nút "Xem chi tiết" của từng việc làm dẫn sang trang chi tiết tin tuyển dụng).
  - Nguồn: `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:21`.

- `CandidateJobDetailView`: đại diện cho Trang chi tiết việc làm (`CandidateJobDetailPage.tsx:44`), hiển thị toàn bộ nội dung chi tiết của một tin tuyển dụng:
  - Thuộc tính dữ liệu hiển thị: `outJobHeader`, `outJobMeta`, `outDescription`, `outRequirements`, `outResponsibilities`, `outBenefits`, `outRequiredSkills`, `outPreferredSkills`.
  - Thuộc tính nút bấm/thao tác: `subBack`, `subReviewInterview`.
  - Nguồn: `source/recruit_system/frontend/src/pages/candidate/CandidateJobDetailPage.tsx:44`.

Điều hướng giữa các lớp biên:
- Từ `CandidateHomeView`, ứng viên nhấn "Xem xếp hạng" (`subViewMatching`) chuyển sang `CandidateMatchingView` (`source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:141`).
- Từ `CandidateMatchingView`, ứng viên nhấn "Xem chi tiết" (`outsubJobDetail`) trên một mục công việc chuyển sang `CandidateJobDetailView` (`source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:158`).
- Từ `CandidateJobDetailView`, ứng viên nhấn "Quay lại" (`subBack`) để trở về `CandidateMatchingView` (`source/recruit_system/frontend/src/pages/candidate/CandidateJobDetailPage.tsx:77`).
- Từ `CandidateJobDetailView`, do trang chi tiết không bố trí nút ứng tuyển trực tiếp, ứng viên chọn menu "Việc làm" trên thanh điều hướng để quay về `CandidateHomeView` thực hiện nộp đơn ứng tuyển cho vị trí đã chọn (`source/recruit_system/frontend/src/pages/candidate/CandidateJobDetailPage.tsx:67`, `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:36`).
- Các nút "Cập nhật CV", "Tải CV" chuyển sang chức năng M2 (`/candidate/cv`) và các nút "Ôn tập phỏng vấn" chuyển sang chức năng M4 (`/candidate/interview`), nằm ngoài phạm vi biểu đồ M3 nên không tạo lớp biên bên ngoài.

**Bước 2.** Với các xử lý dữ liệu chính, sử dụng các hàm nghiệp vụ có thật trong các tầng Service phía backend (`JobService`, `MatchingService`, `ApplicationService`, `CvService`), phân công chúng cho các lớp thực thể chủ thể tương ứng trong mô hình phân tích:

- Tên hàm: `list()`
  - Input: `keyword: String`, `city: String`, `status: String` (tùy chọn; mặc định lấy trạng thái `PUBLISHED`).
  - Output: `List<JobResponse>` (danh sách tin tuyển dụng phù hợp điều kiện tìm kiếm và địa điểm).
  - Lớp chủ thể: `Job`.
  - Nguồn: `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/JobService.java:33`.

- Tên hàm: `getById()`
  - Input: `id: Integer` (mã định danh tin tuyển dụng).
  - Output: `JobResponse` (thông tin chi tiết tin tuyển dụng, danh sách kỹ năng liên kết và công ty tuyển dụng).
  - Lớp chủ thể: `Job`.
  - Nguồn: `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/JobService.java:44`.

- Tên hàm: `myMatches()`
  - Input: Không có tham số tường minh; định danh ứng viên được trích xuất từ phiên xác thực JWT.
  - Output: `List<MatchResponse>` (danh sách kết quả đối sánh đã lưu trong CSDL của ứng viên, sắp xếp theo điểm tổng thể giảm dần).
  - Lớp chủ thể: `MatchingResult`.
  - Nguồn: `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/MatchingService.java:35`.

- Tên hàm: `refreshMine()`
  - Input: Không có tham số tường minh; hệ thống lấy hồ sơ CV đã phân tích của ứng viên hiện tại và duyệt qua tất cả tin tuyển dụng đang mở (`PUBLISHED`).
  - Output: `List<MatchResponse>` (danh sách kết quả đối sánh mới sau khi dịch vụ AI `cv-matching-ai` chấm điểm, lưu vào bảng `matching_results` và sắp xếp theo điểm giảm dần).
  - Lớp chủ thể: `MatchingResult`.
  - Nguồn: `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/MatchingService.java:48`.

- Tên hàm: `apply()`
  - Input: `jobId: Integer` (mã tin tuyển dụng), `request: ApplyRequest` (thư giới thiệu tùy chọn).
  - Output: `ApplicationResponse` (bản ghi đơn ứng tuyển mới được lưu với trạng thái `SUBMITTED`).
  - Lớp chủ thể: `JobApplication`.
  - Nguồn: `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/ApplicationService.java:26`.

- Tên hàm: `mine()`
  - Input: Không có tham số tường minh; xác định ứng viên từ phiên đăng nhập.
  - Output: `CvFormResponse` (thông tin tệp CV, các trường đã trích xuất và cờ `analyzed`).
  - Lớp chủ thể: `CvData`.
  - Ghi chú: Đã trình bày ở chức năng M2.
  - Nguồn: `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:47`.

Các hàm trên trong mã nguồn thực tế thuộc các Spring Service (`JobService`, `MatchingService`, `ApplicationService`, `CvService`), không phải phương thức khai báo trực tiếp trên entity JPA. Việc gán các phương thức này vào các lớp thực thể `Job`, `MatchingResult`, `JobApplication`, `CvData` là tuân thủ nguyên tắc phân công trách nhiệm (operations) trong pha phân tích theo mẫu báo cáo PTIT. Lớp biên chỉ chứa thuộc tính giao diện, không chứa phương thức.

Giữ các lớp thực thể liên quan từ biểu đồ trích lớp thực thể (`TT.json`) gồm `Job`, `Company`, `Skill`, `JobSkill`, `MatchingResult`, `JobApplication`, `CandidateProfile`, `User`, `CvData` với thuộc tính không ghi kiểu và các quan hệ đối tượng:
- Một `Company` có nhiều `Job` (`Job` n – `Company` 1) (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/Job.java:26`).
- `Job` và `Skill` có quan hệ nhiều–nhiều thông qua lớp trung gian `JobSkill` (`JobSkill` n – `Job` 1, `JobSkill` n – `Skill` 1) (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/JobSkill.java:23, 27`).
- `CandidateProfile` và `Job` có quan hệ nhiều–nhiều thông qua đơn ứng tuyển `JobApplication` (`JobApplication` n – `CandidateProfile` 1, `JobApplication` n – `Job` 1) (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/JobApplication.java:25, 29`).
- `MatchingResult` lưu kết quả đối sánh gắn giữa `CandidateProfile` và `Job` (`MatchingResult` n – `CandidateProfile` 1, `MatchingResult` n – `Job` 1) (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/MatchingResult.java:27, 34`).
- Nhiều `CvData` thuộc về một `CandidateProfile` (`CvData` n – `CandidateProfile` 1) (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/CvData.java:20`).
- `CandidateProfile` và `Job` tham chiếu logic tới `User` qua định danh giữa các service (`CandidateProfile` 1 – `User` 1, `Job` n – `User` 1) (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/CandidateProfile.java:26`, `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/Job.java:29`), không khẳng định có khóa ngoại liên service trong CSDL.

Các lớp biên liên kết tới các lớp thực thể có hàm được gọi:
- `CandidateHomeView` gọi `list()` trên `Job`, `myMatches()` trên `MatchingResult`, `apply()` trên `JobApplication`, và `mine()` trên `CvData`.
- `CandidateMatchingView` gọi `mine()` trên `CvData`, `list()` trên `Job`, `myMatches()` và `refreshMine()` trên `MatchingResult`.
- `CandidateJobDetailView` gọi `getById()` trên `Job`.

Ta được biểu đồ lớp pha phân tích chức năng đối sánh CV với việc làm, xem chi tiết việc, ứng tuyển:

### open_questions

- [cần xác nhận] Vị trí nút ứng tuyển: Trang chi tiết việc làm (`CandidateJobDetailPage.tsx`) trong mã nguồn hiện chỉ có nút "Ôn tập phỏng vấn" dẫn sang M4 mà không có nút "Ứng tuyển" trực tiếp (ứng viên phải quay lại trang chủ để nộp đơn). Trong các pha thiết kế tiếp theo (lớp chi tiết, tuần tự) có cần bổ sung nút ứng tuyển ngay trên trang chi tiết việc làm hay giữ nguyên hiện trạng mã nguồn?
- [cần xác nhận] Xử lý ngoại lệ xác thực 401/403: Khi phiên đăng nhập hết hạn hoặc người dùng sai vai trò khi gọi API đối sánh/ứng tuyển, giao diện hiện chỉ hiển thị toast thông báo lỗi mà chưa điều hướng tự động về trang đăng nhập `/login`.
- [cần xác nhận] Ràng buộc CV khi ứng tuyển: Backend `ApplicationService.apply` không kiểm tra CV đã phân tích (`analyzed = true`), trong khi trang chủ ứng viên chỉ hiển thị điểm đối sánh khi cờ `analyzed = true`. Có cần bổ sung tiền điều kiện bắt buộc có CV đã phân tích khi ứng tuyển trong tài liệu thiết kế không?
