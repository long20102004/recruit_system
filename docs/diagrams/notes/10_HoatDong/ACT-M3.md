# ACT-M3 — Biểu đồ hoạt động chức năng Đối sánh CV với việc làm, xem chi tiết việc và ứng tuyển

**Bước 1.** Từ biểu đồ lớp chi tiết CLS-M3, xác định ba làn giao diện tương ứng với các trang chức năng gồm `CandidateHomePage.tsx`, `CandidateMatchingPage.tsx` và `CandidateJobDetailPage.tsx`. Bổ sung làn `client` (đóng vai trò HTTPClient với `api<T>()` và `fetch()`), các làn cho từng Controller gồm `MatchingController`, `JobsController`, `ApplicationsController` (đóng vai trò tiếp nhận và ánh xạ requestMapping), làn `Service/Repository` cho tầng dịch vụ nghiệp vụ và truy vấn dữ liệu (`MatchingService`, `JobService`, `ApplicationService`, `MatchingResultRepository`), cùng làn `AI` cho dịch vụ đối sánh thông minh FastAPI `cv-matching-ai`.

**Bước 2.** Xác định các action trong từng làn (chuẩn hóa theo mẫu PTIT: Hiện giao diện, Lấy từ form, Lưu vào state, Lấy từ state, Gọi hàm f(), Thông báo, cùng fetch() của client và handler của controller):

- **CandidateHomePage.tsx:** Bắt đầu; hiện giao diện CandidateHomePage; lấy từ state: cvReady; lấy từ state: selectedId (sau khi quay lại từ trang chi tiết); lấy từ form: jobId; gọi hàm `applicationsApi.apply(jobId)`; kiểm tra kết quả ứng tuyển; thông báo lỗi nộp hồ sơ khi thất bại; thông báo "Đã nộp hồ sơ ứng tuyển" khi thành công; kết thúc.
- **CandidateMatchingPage.tsx:** Hiện giao diện CandidateMatchingPage; gọi hàm `matchingApi.refreshMine()`; kiểm tra kết quả đối sánh; thông báo lỗi đối sánh khi thất bại; lưu vào state: matches, jobs khi thành công; hiện giao diện danh sách việc phù hợp; lấy từ state: selectedId để xem chi tiết.
- **CandidateJobDetailPage.tsx:** Hiện giao diện CandidateJobDetailPage; gọi hàm `jobsApi.get(id)`; kiểm tra kết quả tải tin; thông báo "Không tìm thấy tin tuyển dụng" khi thất bại; lưu vào state: job khi thành công; hiện giao diện chi tiết việc làm.
- **client:** Thực hiện `api<T>() / fetch()` gửi HTTP request sang backend và trả kết quả đối sánh, chi tiết việc, hoặc kết quả ứng tuyển về cho giao diện (luồng hai chiều).
- **MatchingController:** Tiếp nhận yêu cầu tại handler `refreshMine()` (`POST /api/matching/mine/refresh`), chuyển tiếp sang service và trả kết quả `List<MatchResponse>`.
- **JobsController:** Tiếp nhận yêu cầu tại handler `get()` (`GET /api/jobs/{id}`), chuyển tiếp sang service và trả kết quả `JobResponse`.
- **ApplicationsController:** Tiếp nhận yêu cầu tại handler `apply()` (`POST /api/applications/jobs/{jobId}`), chuyển tiếp sang service và trả kết quả `ApplicationResponse`.
- **Service/Repository:** Gọi hàm `MatchingService.refreshMine()` điều phối trích xuất và chấm điểm, gọi hàm `MatchingResultRepository.findByCandidateId()` lưu/lấy kết quả; gọi hàm `JobService.getById()` truy vấn thông tin việc làm; gọi hàm `ApplicationService.apply()` kiểm tra điều kiện và lưu đơn ứng tuyển mới.
- **AI:** Tiếp nhận yêu cầu qua `match_without_llm()` (`POST /match/no-llm`), thực hiện chuẩn hóa dữ liệu CV–JD, trích xuất đặc trưng và tính toán điểm phù hợp cùng lý do đối sánh.

Mỗi yêu cầu từ giao diện đi qua client, controller, service/repository (và AI nếu là đối sánh), sau đó trả kết quả ngược lại qua controller, client về giao diện theo đúng luồng hai chiều. Kết quả trả về được kiểm tra tại các điểm rẽ nhánh (decision): nhánh thất bại kích hoạt thông báo lỗi và kết thúc luồng qua guard `[Click OK]`; nhánh thành công cập nhật state, kết xuất dữ liệu và cho phép người dùng tiếp tục thao tác điều hướng hoặc nộp hồ sơ. Tổng số nút được giới hạn tối ưu là 40 nút, bảo đảm tính mạch lạc và tuân thủ quy chuẩn.

Ta được biểu đồ hoạt động:

**Lưu ý đối chiếu nguồn.**
- Thao tác nộp đơn ứng tuyển (`apply`) trong mã nguồn thật chỉ được kích hoạt tại Trang chủ ứng viên `CandidateHomePage.tsx` (`source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:91, 212`). Trang chi tiết việc `CandidateJobDetailPage.tsx` (`source/recruit_system/frontend/src/pages/candidate/CandidateJobDetailPage.tsx:44-167`) chỉ hiển thị thông tin tuyển dụng đầy đủ và nút điều hướng ôn tập phỏng vấn, không bố trí nút ứng tuyển trực tiếp.
- Cơ chế đối sánh trong `MatchingService.refreshMine()` duyệt tuần tự các tin tuyển dụng ở trạng thái `JobStatus.PUBLISHED`, gửi dữ liệu sang endpoint AI không dùng LLM `/match/no-llm` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/MatchingService.java:48-61`; `source/recruit_system/services/cv-matching-ai/app/main.py:91`).
- Các hàm và route gọi trong sơ đồ hoàn toàn khớp với biểu đồ lớp chi tiết CLS-M3 và mã nguồn triển khai thực tế.

### Câu hỏi mở

- Không có (toàn bộ các lớp giao diện, client, controller, service, repository và route AI đã được đối chiếu khớp 100% với CLS-M3 và source code).
