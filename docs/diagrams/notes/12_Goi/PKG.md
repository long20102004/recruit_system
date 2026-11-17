# Biểu đồ gói - Các chức năng M1–M4

**Bước 1.** Tập hợp các lớp giao diện và lớp hạ tầng từ `CLS-M1` đến `CLS-M4`, đồng thời lấy các thực thể và quan hệ thực thể đã thiết kế trong `E1`.

**Bước 2.** Tổ chức các trang ứng viên trong gói `View/Candidate`; các trang xác thực, chọn vai trò và `AuthProvider` trong `View/Auth`. Không có trang Recruiter trong các lớp chi tiết M1–M4 nên không tạo gói con Recruiter. `client.ts` và các API client nằm trong `Client`.

**Bước 3.** Chia `Controller`, `Service`, `Repository` theo ba service identity, recruitment, interview. Các thực thể được chia theo service trong `Entity`; các route/module AI lấy từ lớp chi tiết được nhóm trong `AI`.

**Bước 4.** Đưa các lớp vào gói bằng trường `parent`, chỉ biểu diễn tên lớp trong gói; giữ các quan hệ dependency/association và quan hệ giữa thực thể có trong các nguồn CLS/E1. Các tham chiếu qua service là logical, không hàm ý có khóa ngoại vật lý.

Các gói chứa:

- `View/Auth`: `RegisterPage`, `LoginPage`, `ChooseRolePage`, `AuthProvider`.
- `View/Candidate`: các trang `CandidateHomePage.tsx`, `CandidateMatchingPage.tsx`, `CandidateJobDetailPage`, `CandidateCvPage`, `CandidateInterviewPage`.
- `Client`: `client.ts`, `ApiClient`, `authApi`, `cvsApi`, `interviewsApi`.
- `Controller/identity`: `AuthController`.
- `Controller/recruitment`: `JobsController`, `CvController`, `MatchingController`, `ApplicationsController`, `ProfileProvisioningFilter`.
- `Controller/interview`: `InterviewController`.
- `Service/identity` và `Repository/identity`: `AuthService`, `UserRepository`.
- `Service/recruitment` và `Repository/recruitment`: các lớp dịch vụ xử lý hồ sơ/CV, việc làm, ứng tuyển, đối sánh, provisioning và các repository tương ứng.
- `Service/interview` và `Repository/interview`: `InterviewService`, `QuestionSelectionService`, `AiScoringClient` và các repository được thể hiện trong CLS-M4.
- `Entity/identity`: `User`.
- `Entity/recruitment`: `CandidateProfile`, `RecruiterProfile`, `Company`, `CvData`, `Job`, `Skill`, `JobSkill`, `JobApplication`, `MatchingResult`.
- `Entity/interview`: `InterviewSession`, `InterviewSessionQuestion`, `InterviewQuestion`, `InterviewResponse`, `EvaluationResult`, `EvaluationRubric`, `ModelVersion`.
- `AI`: các route/module FastAPI và module/client AI được đưa vào CLS-M2, M3, M4, gồm `routes`, `generator`, `main`, `CvMatchingModule`, `AiJsonClient`, `FastApiApp`, `ScoringModule`.

`Recruiter` không được tạo vì không có trang Recruiter trong phạm vi M1–M4. Gói AI được giữ chung theo yêu cầu, không suy diễn package con cho các dịch vụ AI khác nhau.

Ta được biểu đồ gói:
