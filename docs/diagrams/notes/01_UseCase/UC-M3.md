# Biểu đồ use case chi tiết - Đối sánh CV với việc làm, xem chi tiết việc, ứng tuyển

## Bước 1: Sao chép actor và use case chính
- **Actor:** Ứng viên (vai trò `CANDIDATE`).
- **Use case chính:** "Đối sánh CV với việc làm, xem chi tiết việc, ứng tuyển" (Module M3).
- **Ngữ cảnh:** Ứng viên sau khi đăng nhập và có vai trò hợp lệ tương tác với hệ thống qua các route được bảo vệ (`/candidate`, `/candidate/matching`, `/candidate/jobs/:jobId`) để duyệt tin tuyển dụng, xem danh sách việc làm được AI chấm điểm và xếp hạng phù hợp với CV, xem thông tin chi tiết công việc và nộp hồ sơ ứng tuyển.

## Bước 2: Xác định các use case chi tiết theo giao diện
Căn cứ theo mã nguồn frontend và backend thực tế trong `source/recruit_system/`, chức năng M3 bao gồm 3 màn hình giao diện chính và các hành vi/thao tác cụ thể:
1. **Trang chủ việc làm ứng viên (`CandidateHomePage.tsx`, route `/candidate`):**
   - Hiển thị danh sách việc làm theo khu vực hoặc chế độ việc làm phù hợp CV, tóm tắt thông tin công việc được chọn trên bảng bên phải (`SidePanel`), hiển thị việc làm có điểm phù hợp cao nhất (`Gợi ý tốt nhất`), nút "Xem xếp hạng" điều hướng sang trang đối sánh.
   - Chứa thanh tìm kiếm (`SearchBar`) và các chip lọc (`FilterChips`) để lọc theo từ khóa, địa điểm và chế độ xem việc.
   - Chứa thao tác ứng tuyển (`apply`) khi ứng viên bấm nút "Ứng tuyển" (gọi `applicationsApi.apply(jobId)` tới endpoint `POST /api/applications/jobs/{jobId}`).
   - Các use case chi tiết tương ứng:
     - `Xem việc làm tại trang chủ` (giao diện chính).
     - `Tìm kiếm và lọc việc làm` (thao tác lọc trên giao diện).
     - `Nộp hồ sơ ứng tuyển` (hành động ứng tuyển).
2. **Trang việc làm phù hợp CV (`CandidateMatchingPage.tsx`, route `/candidate/matching`):**
   - Kiểm tra CV đã phân tích (`analyzed`), tải danh sách tin tuyển dụng và điểm đối sánh đã lưu (`matchingApi.mine()`), tự động gọi làm mới điểm (`matchingApi.refreshMine()`) và xếp hạng giảm dần theo điểm tổng thể (`overallScore`).
   - Cung cấp nút "Cập nhật theo CV" (`rematch()`) để yêu cầu backend gọi dịch vụ AI `cv-matching-ai` (`POST /match/no-llm`) tính toán lại điểm đối sánh theo hồ sơ CV hiện tại.
   - Nút "Xem chi tiết" dẫn sang trang chi tiết tin tuyển dụng.
   - Các use case chi tiết tương ứng:
     - `Xem danh sách việc làm phù hợp CV` (giao diện chính).
     - `Cập nhật điểm đối sánh theo CV` (thao tác làm mới điểm đối sánh).
3. **Trang chi tiết việc làm (`CandidateJobDetailPage.tsx`, route `/candidate/jobs/:jobId`):**
   - Tải và hiển thị toàn bộ nội dung chi tiết tin tuyển dụng: tiêu đề, công ty, địa điểm, hình thức làm việc, mức lương, kinh nghiệm, mô tả công việc, yêu cầu, trách nhiệm, đãi ngộ, kỹ năng bắt buộc và kỹ năng ưu tiên.
   - Cung cấp nút "Quay lại" trang đối sánh và nút "Ôn tập phỏng vấn" (chuyển tiếp sang Module M4).
   - Use case chi tiết tương ứng: `Xem chi tiết việc làm`.

## Bước 3: Xác định quan hệ include và extend
- **Quan hệ `<<include>>` (bước bắt buộc):**
  - Use case chính bao gồm hai giao diện duyệt danh sách bắt buộc:
    - `Xem việc làm tại trang chủ`: Ứng viên truy cập để xem danh sách việc làm và tóm tắt thông tin.
    - `Xem danh sách việc làm phù hợp CV`: Ứng viên truy cập để xem danh sách công việc được hệ thống đối sánh và chấm điểm phù hợp dựa trên CV đã trích xuất.
- **Quan hệ `<<extend>>` (bước tùy chọn):**
  - `Tìm kiếm và lọc việc làm`: Ứng viên tùy chọn nhập từ khóa, chọn thành phố hoặc đổi chế độ lọc trên trang chủ tại extension point *"Tìm kiếm và lọc việc làm"*.
  - `Cập nhật điểm đối sánh theo CV`: Ứng viên tùy chọn bấm nút "Cập nhật theo CV" trên trang đối sánh để AI tính lại điểm số tại extension point *"Cập nhật điểm đối sánh theo CV"*.
  - `Xem chi tiết việc làm`: Từ danh sách công việc phù hợp, ứng viên tùy chọn bấm "Xem chi tiết" để mở trang chi tiết một tin tuyển dụng cụ thể tại extension point *"Xem chi tiết việc làm"*.
  - `Nộp hồ sơ ứng tuyển`: Ứng viên tùy chọn chọn một vị trí công việc và bấm "Ứng tuyển" tại extension point *"Nộp hồ sơ ứng tuyển"*.

## Bước 4: Mô tả use case chi tiết
- **Đối sánh CV với việc làm, xem chi tiết việc, ứng tuyển:** Cho phép Ứng viên xem danh sách việc làm, đối sánh hồ sơ CV với các tin tuyển dụng, xem chi tiết thông tin công việc và nộp hồ sơ ứng tuyển.
- **Xem việc làm tại trang chủ:** Cho phép Ứng viên duyệt các tin tuyển dụng đang mở, xem thông tin tóm tắt vị trí việc làm được chọn và theo dõi gợi ý công việc phù hợp nhất.
- **Tìm kiếm và lọc việc làm:** Cho phép Ứng viên tìm kiếm theo từ khóa vị trí, lọc việc làm theo tỉnh/thành phố và chuyển đổi giữa chế độ xem việc theo khu vực và xem theo mức độ phù hợp với CV.
- **Xem danh sách việc làm phù hợp CV:** Cho phép Ứng viên xem bảng xếp hạng công việc theo độ phù hợp (%) trích xuất từ CV, kèm phân tích kỹ năng yêu cầu và khoảng trống kỹ năng còn thiếu.
- **Cập nhật điểm đối sánh theo CV:** Cho phép Ứng viên chủ động kích hoạt lại tiến trình đối sánh của dịch vụ AI `cv-matching-ai` để làm mới điểm phù hợp cho tất cả các tin tuyển dụng đang mở.
- **Xem chi tiết việc làm:** Cho phép Ứng viên xem toàn bộ thông tin chi tiết của một tin tuyển dụng gồm mô tả, yêu cầu, trách nhiệm, mức lương, kinh nghiệm và các kỹ năng bắt buộc/ưu tiên.
- **Nộp hồ sơ ứng tuyển:** Cho phép Ứng viên gửi đơn ứng tuyển vào vị trí công việc đã chọn từ trang chủ ứng viên và nhận phản hồi xác nhận nộp hồ sơ thành công từ hệ thống.

Ta được biểu đồ use case chi tiết chức năng “Đối sánh CV với việc làm, xem chi tiết việc, ứng tuyển”:

## Bảng truy vết

| Phần tử / Quan hệ | Loại | Nguồn truy vết |
|---|---|---|
| `HireLens - M3 Đối sánh CV với việc làm, xem chi tiết việc, ứng tuyển` | System | `source/recruit_system/frontend/src/App.tsx:58` |
| `Ứng viên` | Actor | `source/recruit_system/frontend/src/App.tsx:58` (`RequireAuth roles={["CANDIDATE"]}`) |
| `Đối sánh CV với việc làm, xem chi tiết việc, ứng tuyển` | Use Case (chính) | `source/recruit_system/frontend/src/App.tsx:72` |
| `Xem việc làm tại trang chủ` | Use Case | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:36`; `JobsController.java:19` |
| `Tìm kiếm và lọc việc làm` | Use Case | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:109` |
| `Xem danh sách việc làm phù hợp CV` | Use Case | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:21`; `MatchingController.java:18` |
| `Cập nhật điểm đối sánh theo CV` | Use Case | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:67`; `MatchingController.java:23` |
| `Xem chi tiết việc làm` | Use Case | `source/recruit_system/frontend/src/pages/candidate/CandidateJobDetailPage.tsx:44`; `JobsController.java:35` |
| `Nộp hồ sơ ứng tuyển` | Use Case | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:91`; `ApplicationsController.java:18` |
| Association: `Ứng viên` → Use case chính | Quan hệ | `source/recruit_system/frontend/src/App.tsx:58` |
| Association: `Ứng viên` → `Xem việc làm tại trang chủ` | Quan hệ | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:36` |
| Association: `Ứng viên` → `Xem danh sách việc làm phù hợp CV` | Quan hệ | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:21` |
| Include: Use case chính → `Xem việc làm tại trang chủ` | Quan hệ | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:36` |
| Include: Use case chính → `Xem danh sách việc làm phù hợp CV` | Quan hệ | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:21` |
| Extend: `Tìm kiếm và lọc việc làm` → Use case chính | Quan hệ | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:109` |
| Extend: `Cập nhật điểm đối sánh theo CV` → Use case chính | Quan hệ | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:67` |
| Extend: `Xem chi tiết việc làm` → Use case chính | Quan hệ | `source/recruit_system/frontend/src/pages/candidate/CandidateJobDetailPage.tsx:44` |
| Extend: `Nộp hồ sơ ứng tuyển` → Use case chính | Quan hệ | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:91` |

## Mâu thuẫn tài liệu – mã nguồn

1. **Vị trí thao tác ứng tuyển:** Trong mô tả tổng quan chức năng, luồng thường được giả định là xem chi tiết công việc rồi mới bấm ứng tuyển. Tuy nhiên trong mã nguồn frontend thực tế (`CandidateJobDetailPage.tsx:154-160`), trang chi tiết việc làm **không có nút ứng tuyển**, mà chỉ có nút "Ôn tập phỏng vấn" dẫn sang Module M4. Thao tác ứng tuyển thực tế chỉ có mặt tại trang chủ ứng viên (`CandidateHomePage.tsx:212` và `JobCard.tsx:64-67`).
2. **Khác biệt đánh số module trong tài liệu:** Tài liệu `source/recruit_system/docs/Module3_Interview_Flow.md` gọi chức năng luyện phỏng vấn là "Module 3", trong khi danh mục phân chia báo cáo hệ thống chuẩn hóa chức năng M3 là "Đối sánh CV với việc làm, xem chi tiết việc, ứng tuyển" (còn luyện phỏng vấn thuộc Module M4).
3. **Độ phụ thuộc CV khi ứng tuyển:** Backend (`ApplicationService.java:26-38`) không yêu cầu ứng viên phải có CV đã phân tích (`analyzed`) khi nộp đơn ứng tuyển, trong khi luồng đối sánh (`MatchingService.java:48-52`) bắt buộc phải có CV đã phân tích.

## Open questions

1. Trang chi tiết việc làm (`CandidateJobDetailPage.tsx`) hiện chỉ có nút "Ôn tập phỏng vấn" sang Module M4 mà không có nút "Ứng tuyển"; ứng viên phải quay lại trang chủ mới có thể nộp đơn ứng tuyển. Cần xác nhận với nhóm phát triển/người dùng xem trong bản vẽ thiết kế báo cáo có cần đề xuất bổ sung nút "Ứng tuyển" ngay trên trang chi tiết công việc hay giữ nguyên thiết kế theo đúng hiện trạng mã nguồn.
