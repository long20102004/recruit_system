# Thiết kế biểu đồ tuần tự chức năng M2: Tải và xác nhận CV

**Bước 1.** Phân tích phạm vi chức năng theo kịch bản chuẩn KB-M2: chức năng M2 gồm hai giai đoạn tương tác tuần tự trong luồng chính:
- Giai đoạn 1 (Tải và trích xuất CV bằng AI): Ứng viên tải lên tệp CV PDF (ví dụ `CV_Nguyen_Minh_An.pdf`), hệ thống kiểm tra tệp, đọc văn bản PDF, gọi dịch vụ AI trích xuất thông tin có cấu trúc và lưu các trường nháp vào cơ sở dữ liệu.
- Giai đoạn 2 (Rà soát và xác nhận hồ sơ): Ứng viên kiểm tra các trường đã được điền tự động, chỉnh sửa nội dung nếu cần và nhấn "Xác nhận hồ sơ"; hệ thống cập nhật các trường vào cơ sở dữ liệu, đồng bộ thông tin và chuyển giao diện về chế độ "Hồ sơ của bạn".

**Bước 2.** Xác định các đối tượng tham gia theo biểu đồ lớp chi tiết CLS-M2, sắp xếp theo thứ tự từ trái sang phải:
- Tác nhân: Ứng viên (`actor`).
- Tầng giao diện (stereotype `boundary`): `:CandidateCvPage.tsx` đại diện cho trang quản lý và tải CV phía React.
- Tầng điều khiển và dịch vụ (stereotype `control`):
  - `:client`: module API client phía Frontend thực hiện lời gọi `api()` và `fetch()`.
  - `:CvController`: Spring REST Controller tiếp nhận request định tuyến từ API Gateway.
  - `:CvService`: tầng dịch vụ nghiệp vụ xử lý logic tải tệp, kiểm tra điều kiện và xác nhận hồ sơ.
  - `:CvExtractionModule`: module trung gian đọc text PDF và điều phối gọi sang dịch vụ AI trích xuất.
  - `:routes`: endpoint FastAPI `/api/v1/extract-cv` của dịch vụ `cv-extraction-ai`.
  - `:CvDataRepository`: Spring Data JPA repository thao tác dữ liệu trên bảng `cv_data`.
- Tầng thực thể (stereotype `entity`):
  - `:CvData`: thực thể dữ liệu lưu trữ từng trường thông tin hồ sơ của ứng viên.

**Bước 3. Kịch bản chuẩn V3**

1. Ứng viên chọn hoặc kéo thả tệp CV PDF (`CV_Nguyen_Minh_An.pdf`) vào vùng tải tệp trên CandidateCvPage.tsx.
2. CandidateCvPage.tsx gọi client qua phương thức cvsApi.upload(file).
3. client thực hiện fetch() và api() để chuẩn bị FormData và gửi yêu cầu mạng.
4. client gửi yêu cầu HTTP POST /api/cvs tới CvController qua API Gateway.
5. CvController thực hiện upload() tiếp nhận tệp tải lên.
6. CvController gọi CvService.upload(file).
7. CvService thực hiện upload(), kiểm tra định dạng PDF và trạng thái hồ sơ ứng viên.
8. CvService gọi CvExtractionModule.extract(pdfBytes).
9. CvExtractionModule thực hiện extract(), gọi PdfTextExtractor đọc văn bản từ nội dung tệp.
10. CvExtractionModule gửi yêu cầu phân tích tới routes qua HTTP POST /api/v1/extract-cv?include=kg.
11. routes thực hiện extract_cv(), sinh cấu trúc hồ sơ và chuẩn hóa kỹ năng qua đồ thị tri thức.
12. routes trả kết quả trích xuất JSON cho CvExtractionModule.
13. CvExtractionModule trả dữ liệu trích xuất cho CvService.
14. CvService gọi CvDataRepository.findByCandidateIdAndFieldOrderByIdAsc() để tra cứu các bản ghi hiện có.
15. CvDataRepository thực hiện truy vấn tìm kiếm dữ liệu cũ theo ứng viên và trường.
16. CvDataRepository trả danh sách bản ghi cũ cho CvService.
17. CvService gọi CvData để tạo mới đối tượng bản ghi cho từng trường trích xuất.
18. CvData thực hiện CvData(), setter() thiết lập candidateId, field và value tương ứng.
19. CvData trả đối tượng thực thể cho CvService.
20. CvService gọi CvDataRepository.save(cvData) để ghi nhận trường dữ liệu vào CSDL.
21. CvDataRepository thực hiện save() lưu bản ghi vào bảng cv_data.
22. CvDataRepository hoàn tất lưu và trả kết quả cho CvService.
23. CvService đóng gói kết quả CvFormResponse và trả về cho CvController.
24. CvController trả phản hồi HTTP 200 kèm biểu mẫu CV cho client.
25. client phân tích dữ liệu JSON và trả kết quả cho CandidateCvPage.tsx.
26. CandidateCvPage.tsx thực hiện applyForm() cập nhật state và chuyển sang bước 2 (Kiểm tra).
27. CandidateCvPage.tsx hiển thị thông báo "Đã tải CV và điền các mục hồ sơ. Hãy kiểm tra trước khi xác nhận." và các trường trích xuất cho Ứng viên.
28. Ứng viên rà soát, chỉnh sửa nội dung các trường nếu cần và chọn "Xác nhận hồ sơ".
29. CandidateCvPage.tsx gọi client qua phương thức cvsApi.confirm(fields).
30. client thực hiện fetch() và api() gửi dữ liệu JSON các trường hồ sơ.
31. client gửi yêu cầu HTTP PUT /api/cvs tới CvController qua API Gateway.
32. CvController thực hiện confirm() tiếp nhận yêu cầu xác nhận.
33. CvController gọi CvService.confirm(request).
34. CvService thực hiện confirm(), kiểm tra tên tệp đã lưu và danh mục trường cấu hình cho phép.
35. CvService gọi CvDataRepository.findByCandidateIdAndFieldOrderByIdAsc() trong replaceLines() để chuẩn bị thay thế dữ liệu.
36. CvDataRepository thực hiện truy vấn tìm kiếm các dòng dữ liệu cũ của trường.
37. CvDataRepository trả danh sách bản ghi cũ cho CvService.
38. CvService gọi CvData để tạo bản ghi mới với nội dung đã được ứng viên xác nhận.
39. CvData thực hiện CvData(), setter() thiết lập dữ liệu dòng đã được làm sạch.
40. CvData trả đối tượng thực thể cho CvService.
41. CvService gọi CvDataRepository.save(cvData) để lưu trường đã xác nhận.
42. CvDataRepository thực hiện save() lưu bản ghi đã xác nhận vào bảng cv_data.
43. CvDataRepository hoàn tất lưu và trả kết quả cho CvService.
44. CvService đóng gói kết quả CvFormResponse đã cập nhật và trả về cho CvController.
45. CvController trả phản hồi HTTP 200 cho client.
46. client đọc dữ liệu JSON và trả kết quả cho CandidateCvPage.tsx.
47. CandidateCvPage.tsx thực hiện applyForm() cập nhật state sang bước 3 (Xem hồ sơ).
48. CandidateCvPage.tsx hiển thị thông báo "Đã xác nhận hồ sơ" và hiển thị giao diện "Hồ sơ của bạn" cho Ứng viên.

**Bước 4.** Biểu diễn từng bước bằng thông điệp với số thứ tự tương ứng từ 1 đến 48. Lời gọi giữa các lifeline dùng nhãn `call`, lời gọi nội bộ tự xử lý dùng self-message (`fetch()`, `upload()`, `extract()`, `extract_cv()`, `confirm()`, `findByCandidateIdAndFieldOrderByIdAsc()`, `save()`, `applyForm()`, `CvData(), setter()`), kết quả trả về từng tầng dùng `return`, và thông báo kết quả ra giao diện cho ứng viên dùng `show`.

Ta được biểu đồ tuần tự chức năng M2 – tải và xác nhận CV:

### Ghi chú

- Toàn bộ 9 đối tượng lifeline trong biểu đồ tuần tự đều nằm trong biểu đồ lớp chi tiết CLS-M2, đảm bảo tính nhất quán và truy vết đầy đủ giữa các tầng kiến trúc Microservices (Frontend React Vite, Backend Spring Boot, AI FastAPI).
- Đối tượng `CvData` trong mã nguồn Spring Boot được quản lý thông qua thư viện Lombok (`@Builder`, `@Getter`, `@Setter`), tương ứng với thao tác khởi tạo đối tượng và setter trong mẫu báo cáo chuẩn PTIT.
- Các thao tác truy vấn `findByCandidateIdAndFieldOrderByIdAsc()` và lưu `save()` là các phương thức của Spring Data JPA tương đương với tầng DAO trong kiến trúc truyền thống.
- Nhánh ngoại lệ chính: Trong trường hợp tệp tải lên không phải định dạng PDF, hỏng hoặc vượt quá giới hạn 10 trang, `PdfTextExtractor` phát ngoại lệ và `CvExtractionModule` chuyển đổi thành mã lỗi HTTP 400 (`Invalid PDF or too many pages`), hệ thống ngắt luồng trích xuất và hiển thị thông báo lỗi trên giao diện mà không tiếp tục lưu CSDL hay gọi dịch vụ AI. Luồng chuẩn V3 trên biểu diễn nhánh xử lý thành công toàn vẹn.
- Lời gọi đồng bộ Họ tên và Điện thoại sang `identity-service` (`IdentityClient.update()`) và kiểm tra quyền ứng viên (`requireCandidate()`) được đóng gói bên trong `CvService.confirm()` và `CvService.upload()`, không vẽ thêm lifeline để giữ số lượng lifeline trong giới hạn trực quan (9 lifeline ≤ 10).

### Vấn đề cần xác nhận

- [cần xác nhận] Đích điều hướng cụ thể khi phiên đăng nhập hết hạn hoặc người dùng không có vai trò CANDIDATE và API trả về 401/403 (trên FE RequireAuth chặn sang /login hoặc /choose-role).
- [cần xác nhận] Cơ chế xử lý file PDF scan/ảnh không có text layer: hiện tại PdfTextExtractor kiểm tra độ dài text < 50 ký tự và trả HTTP 422, chưa tích hợp OCR.
