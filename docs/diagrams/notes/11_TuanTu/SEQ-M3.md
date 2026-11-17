# Thiết kế biểu đồ tuần tự chức năng M3: Ứng tuyển tại trang chủ

**Bước 1.** Chọn lát cắt ứng tuyển thành công tại trang chủ ứng viên (bước 10–13 của kịch bản M3). Điều kiện: ứng viên đã đăng nhập, tin đang mở và chưa có đơn trùng. Các bước tải trang, đối sánh và xem chi tiết đã diễn ra trước đó và không được thể hiện trong hình này.

**Bước 2.** Xác định các đối tượng theo CLS-M3, từ trái sang phải: ứng viên; `CandidateHomePage.tsx` (boundary); `client`, `ApplicationsController`, `ApplicationService`, `JobRepository`, `JobApplicationRepository` (control); `JobApplication` (entity). Module client và React function component được ký hiệu như đối tượng thiết kế.

**Bước 3. Kịch bản chuẩn V3**

1. Ứng viên chọn tin trên trang chủ và nhấn “Ứng tuyển”.
2. CandidateHomePage.tsx gọi client qua applicationsApi.apply(jobId).
3. client thực hiện api() cho POST /api/applications/jobs/{jobId} và fetch(); token được lấy từ localStorage nếu có.
4. client gửi yêu cầu tới ApplicationsController qua API Gateway.
5. ApplicationsController thực hiện apply().
6. ApplicationsController gọi ApplicationService.
7. ApplicationService thực hiện apply(), kiểm tra vai trò và lấy hồ sơ ứng viên.
8. ApplicationService gọi JobRepository.findById(jobId).
9. JobRepository trả kết quả tìm việc cho ApplicationService; service kiểm tra trạng thái PUBLISHED.
10. ApplicationService gọi JobApplicationRepository.findByJobIdAndCandidateId() kiểm tra đơn trùng.
11. JobApplicationRepository trả kết quả kiểm tra cho ApplicationService; luồng chuẩn chưa có đơn.
12. ApplicationService tạo JobApplication bằng builder, truyền job, candidate, status và coverLetter.
13. JobApplication được khởi tạo qua builder() và build(); source không gọi setter trong bước này.
14. JobApplication được tạo trả về ApplicationService.
15. ApplicationService gọi JobApplicationRepository.save(application).
16. JobApplicationRepository hoàn tất save và trả quyền điều khiển cho ApplicationService.
17. ApplicationService tạo ApplicationResponse và trả cho ApplicationsController.
18. ApplicationsController trả phản hồi HTTP cho client.
19. client đọc JSON và trả kết quả cho CandidateHomePage.tsx.
20. CandidateHomePage.tsx hiển thị thông báo “Đã nộp hồ sơ ứng tuyển”.

**Bước 4.** Biểu diễn từng bước bằng message cùng số thứ tự; lời gọi dùng `call`, thực thi dùng self-message, trả kết quả dùng `return`, hiển thị dùng `show`. Lời gọi `requireCandidate()` và `toResponse()` có sử dụng các lớp chưa có trong CLS-M3 nên chỉ mô tả khái quát, không vẽ đối tượng giả.

Ta được biểu đồ tuần tự chức năng M3 – ứng tuyển tại trang chủ:

**Ghi chú:** `JobApplication` được tạo qua Lombok builder, không dùng setter trong luồng này; `save()` và `findById()` là phương thức kế thừa Spring Data. Kết quả ứng tuyển chỉ được dùng để hiện toast. Sơ đồ không thể hiện AI, luồng đối sánh hoặc trang chi tiết do giới hạn số lifeline.

**Vấn đề cần xác nhận:**

- [cần xác nhận] Có tách thêm biểu đồ tuần tự cho đối sánh CV và xem chi tiết việc không? Một hình ≤ 10 lifeline không đủ biểu diễn đầy đủ các lớp riêng của cả ba luồng M3.
- [cần xác nhận] Có bổ sung CandidateProfileRepository và IdentityClient vào CLS-M3 để biểu diễn đầy đủ requireCandidate() và toResponse() không?
