# Thiết kế biểu đồ lớp chi tiết chức năng đối sánh, xem chi tiết việc và ứng tuyển

Giao diện được xây dựng bằng React 19, Vite và TypeScript; backend sử dụng Spring Boot 4.1 và Spring Data JPA; dịch vụ đối sánh CV–JD sử dụng FastAPI. Biểu đồ gộp giao diện, backend và điểm tiếp nhận AI trên cùng một hình.

## Bước 1. Xác định các lớp giao diện

### a. Tầng giao diện

Các tên `txt`, `btn` dưới đây là tên mô hình hóa các điều khiển JSX, không phải biến được khai báo trong mã nguồn. Danh sách việc được hiển thị dưới dạng danh sách/thẻ, không phải bảng.

**CandidateHomePage.tsx** (`frontend/src/pages/candidate/CandidateHomePage.tsx:36`):
- Thuộc tính tường minh: `txtKeyword: input`, `selectCity: select`, `btnSearch: Button`, `btnMode: ChipFilter`, `btnMatching: Button`, `jobList: JobList`, `btnApply: Button`, `btnInterview: Button`; còn có liên kết cập nhật/tải CV. `SearchBar` thực sự dùng `input` cho từ khóa và `select` cho địa điểm (`frontend/src/components/common/SearchBar.tsx:54`).
- Thuộc tính ẩn: `keyword`, `city`, `mode`, `jobs: JobDto[]`, `matches: MatchDto[]`, `cvReady`, `selectedId`; `user` lấy từ `useAuth()` và thông báo qua `useToast()`.
- Có gọi backend: lấy danh sách việc, tình trạng CV và điểm đã lưu; nộp đơn qua `applicationsApi.apply`. Lọc từ khóa/địa điểm theo state ở phía giao diện; `onSubmit` tìm kiếm hiện không thực hiện thêm hành động (`CandidateHomePage.tsx:109–114`).
- Chọn thẻ việc cập nhật khung chi tiết tại chỗ; ứng tuyển không chuyển trang. Xem xếp hạng đến `/candidate/matching`, cập nhật/tải CV đến `/candidate/cv`, ôn tập đến `/candidate/interview?jobId=...`.

**CandidateMatchingPage.tsx** (`frontend/src/pages/candidate/CandidateMatchingPage.tsx:21`):
- Thuộc tính tường minh: `btnRematch: Button`, `btnUploadCv: Button`, `btnJobDetail: Button/link`; danh sách `MatchItem` hoặc danh sách tin khi chưa có điểm, cùng thông báo trạng thái/lỗi.
- Thuộc tính ẩn: `matches`, `jobs`, `ready`, `loading`, `busy`, `scoreError`; `toast` từ context.
- Có gọi backend: `load()` lấy tình trạng CV, danh sách tin, điểm đã lưu và thử cập nhật điểm; nếu tính điểm lỗi, giao diện có thể giữ điểm cũ hoặc hiển thị tin đang mở. `rematch()` gọi lại `load()`.
- Tải CV đến `/candidate/cv`; xem chi tiết đến `/candidate/jobs/{jobId}`. Không có thao tác nộp đơn tại trang này.

**CandidateJobDetailPage.tsx** (`frontend/src/pages/candidate/CandidateJobDetailPage.tsx:44`):
- Thuộc tính tường minh: `btnBack: Button`, `btnInterview: Button`, `jobInfo: Panel`; thông tin gồm tên, công ty, địa điểm, mô tả, yêu cầu, trách nhiệm, đãi ngộ và kỹ năng.
- Thuộc tính ẩn: `jobId` từ route, `job: Job | null`, `loading`, `toast` từ context.
- Có gọi backend qua `jobsApi.get(id)` để lấy chi tiết. Quay lại đến `/candidate/matching`; ôn tập đến `/candidate/interview?jobId=...` hoặc `/candidate/interview`. Trang này không có nút ứng tuyển.

**Quan hệ giữa các giao diện:** `CandidateHomePage.tsx` → `CandidateMatchingPage.tsx` → `CandidateJobDetailPage.tsx` → `CandidateMatchingPage.tsx`; các liên kết CV và ôn tập đi sang chức năng khác. Ảnh chụp giao diện thật cần được bổ sung khi dựng báo cáo; không giả định ảnh đã được tạo.

## Bước 2. Xác định các lớp thao tác cơ sở dữ liệu

### b. Tầng thao tác CSDL

Spring Data JPA cung cấp các interface repository đóng vai trò DAO; service điều phối nghiệp vụ. Không tạo `DAO` hoặc `EntityManager` giả trong sơ đồ. Các phương thức của lát cắt được thể hiện như sau:

| Lớp và phương thức | Input | Output |
|---|---|---|
| `JobService.list` | `keyword: String`, `city: String`, `status: String` | `List<JobDtos.JobResponse>` |
| `JobService.getById` | `id: Integer` | `JobDtos.JobResponse` |
| `CvService.mine` | Không | `CvDtos.CvFormResponse` |
| `MatchingService.myMatches` | Không | `List<MatchingDtos.MatchResponse>` |
| `MatchingService.refreshMine` | Không | `List<MatchingDtos.MatchResponse>` |
| `ApplicationService.apply` | `jobId: Integer`, `request: ApplicationDtos.ApplyRequest` | `ApplicationDtos.ApplicationResponse` |
| `JobRepository.search` | `keyword: String`, `city: String`, `status: JobStatus` | `List<Job>` |
| `CvDataRepository.findByCandidateIdAndFieldOrderByIdAsc` | `candidateId: Integer`, `field: String` | `List<CvData>` |
| `MatchingResultRepository.findByCandidateId` | `candidateId: Integer` | `List<MatchingResult>` |
| `JobApplicationRepository.findByJobIdAndCandidateId` | `jobId: Integer`, `candidateId: Integer` | `Optional<JobApplication>` |

Các repository còn dùng phương thức kế thừa của `JpaRepository`; để giới hạn hình, không khai báo lại các phương thức kế thừa và không vẽ `JobSkillRepository`, `CandidateProfileRepository`. Thực tế các service còn dùng những repository này; không hiểu hình là toàn bộ phụ thuộc của service.

## Bước 3. Xác định lớp thực thể

### c. Tầng thực thể

Hình chọn `CandidateProfile`, `CvData`, `Job`, `JobApplication`, `MatchingResult`; thuộc tính có kiểu và các quan hệ giữa năm thực thể giữ theo E1. `CvData.candidateId` là ID nguyên trong mã, không phải thuộc tính đối tượng JPA; aggregation với `CandidateProfile` là mô hình hóa theo E1. `Decimal` trong E1 tương ứng `BigDecimal` của Java. Do giới hạn 24 lớp/interface, hình không vẽ `Company`, `Skill`, `JobSkill`, `User` và các quan hệ tới chúng; các lớp này vẫn tồn tại và có liên quan đến M3.

## Bước 4. Xác định lớp phụ trợ và quan hệ

### d. Lớp phụ trợ

- Module `client.ts` đảm nhiệm vai trò `HTTPClient.fetch()`: `api<T>(path, options)` gọi `fetch`, gắn bearer token; các nhóm `jobsApi`, `cvsApi`, `matchingApi`, `applicationsApi` gọi các route tương ứng (`frontend/src/api/client.ts:32–116`). Đây là các hàm và object trong module, không phải một lớp JavaScript thật.
- `JobsController`, `CvController`, `MatchingController`, `ApplicationsController` là các REST controller thực, chuyển yêu cầu tới service tương ứng. API đi qua gateway, các nhãn HTTP ghi đường dẫn ngoài `/api/...`.
- `MatchingService` gọi `CvMatchingModule.match(candidate, jd)`, module này dùng `AiJsonClient.post(url, body)` gửi `POST /match/no-llm` tới FastAPI (`backend/recruitment-service/src/main/java/recruit/demo/service/matching/CvMatchingModule.java:17–18`). Route `match_without_llm(request: MatchRequest)` của module `main.py` gọi `_run_match(request, use_llm=False)`, chuẩn hóa đầu vào, trích đặc trưng và tính điểm (`services/cv-matching-ai/app/main.py:57–92`). `main` là module Python được trình bày bằng hộp lớp, không phải lớp thật.

### Phân tích mẫu thiết kế

- **Repository:** các interface Spring Data tách truy vấn và lưu trữ khỏi service; ví dụ `JobRepository.search` tập trung truy vấn danh sách việc, giúp thay đổi truy vấn mà không phải đặt SQL/JPQL vào controller.
- **DTO:** các `JobDtos.JobResponse`, `MatchingDtos.MatchResponse`, `ApplicationDtos.ApplyRequest` và response được dùng ở ranh giới API; dữ liệu gửi đi không cần phơi bày trực tiếp toàn bộ entity.
- **Dependency Injection:** các controller và service nhận phụ thuộc Spring qua constructor (trong nhiều lớp được Lombok sinh từ `@RequiredArgsConstructor`); `CvMatchingModule` nhận `AiJsonClient` và URL cấu hình, giúp thay thế phụ thuộc/cấu hình khi kiểm thử hoặc triển khai.
- **Gateway/Adapter:** nginx định tuyến API công khai đến recruitment-service; `CvMatchingModule` đóng vai trò adapter đóng gói yêu cầu và kiểm tra dữ liệu trả về từ dịch vụ AI, còn `AiJsonClient` thực hiện HTTP JSON. Điều này tách nghiệp vụ đối sánh khỏi giao thức và việc kiểm tra payload AI.

Ta được biểu đồ lớp chi tiết chức năng đối sánh, xem chi tiết việc và ứng tuyển:
