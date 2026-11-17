# Biểu đồ use case tổng quan hệ thống tuyển dụng HireLens

**Bước 1. Xác định hệ thống:** Hệ thống tuyển dụng HireLens được giới hạn trong bốn chức năng M1–M4: đăng ký, đăng nhập và chọn vai trò; tải và xác nhận CV; đối sánh, xem việc và ứng tuyển; ôn tập và chấm phỏng vấn.

**Bước 2. Xác định actor:**

- **Thành viên** là actor khái quát cho người dùng có tài khoản; **Ứng viên** và **Nhà tuyển dụng** là hai actor con, nối với Thành viên bằng generalization. Chọn vai trò yêu cầu người dùng đã đăng nhập.
- **Khách** truy cập trang việc làm công khai, đăng ký hoặc mở trang đăng nhập khi chưa có tài khoản.
- Không vẽ các dịch vụ AI thành actor gián tiếp: chúng là các thành phần triển khai bên trong phạm vi hệ thống HireLens, được backend gọi để hỗ trợ xử lý, không phải tác nhân bên ngoài tương tác độc lập với hệ thống. Actor Thành viên và quan hệ kế thừa là khái quát hóa nghiệp vụ từ kiểm tra vai trò, không khẳng định có lớp actor tương ứng trong mã nguồn.

**Bước 3. Xác định use case và quan hệ:**

- M1 gồm Đăng ký, Đăng nhập, Chọn vai trò; M2 gồm Tải và xác nhận CV; M3 gồm Xem danh sách việc làm công khai, Đối sánh CV với việc làm, Xem chi tiết việc, Ứng tuyển; M4 gồm Ôn tập và chấm phỏng vấn.
- Từ danh sách đối sánh, ứng viên có thể chọn xem chi tiết một việc: **Xem chi tiết việc** `<<extend>>` **Đối sánh CV với việc làm** tại extension point **Xem chi tiết việc**. Danh sách dự phòng khi chưa chấm được cũng có liên kết xem chi tiết.
- **Ứng tuyển** được mô hình hóa độc lập, không `<<extend>>` đối sánh: trang chủ ứng viên cho phép ứng tuyển ngay tại thẻ hoặc bảng bên cạnh, kể cả chế độ theo khu vực. Trang chi tiết việc chỉ có nút ôn tập, không có nút ứng tuyển. Trang công khai chuyển khách muốn ứng tuyển sang đăng ký, không trực tiếp nộp hồ sơ.
- Nhà tuyển dụng cũng dùng đối sánh để làm mới xếp hạng các ứng viên đã ứng tuyển theo tin đã chọn. ADMIN được mã nguồn cho phép vượt kiểm tra vai trò nhưng không vẽ luồng riêng theo phạm vi báo cáo.

**Bước 4. Mô tả use case:**

- **Đăng ký:** cho phép khách tạo tài khoản bằng email và mật khẩu.
- **Đăng nhập:** cho phép khách đăng nhập vào tài khoản; use case được gắn với actor cha Thành viên theo quy ước tổng quát.
- **Chọn vai trò:** cho phép thành viên đã đăng nhập chọn vai trò ứng viên hoặc nhà tuyển dụng.
- **Xem danh sách việc làm công khai:** cho phép khách xem và lọc các tin việc làm đang hiển thị.
- **Tải và xác nhận CV:** cho phép ứng viên tải CV PDF, kiểm tra dữ liệu trích xuất và xác nhận hồ sơ.
- **Đối sánh CV với việc làm:** cho phép ứng viên xem, cập nhật danh sách việc phù hợp và nhà tuyển dụng chạy xếp hạng ứng viên theo tin.
- **Xem chi tiết việc:** cho phép ứng viên chọn một tin từ danh sách đối sánh để xem chi tiết.
- **Ứng tuyển:** cho phép ứng viên nộp hồ sơ vào tin từ trang chủ ứng viên.
- **Ôn tập và chấm phỏng vấn:** cho phép ứng viên tạo phiên, trả lời câu hỏi, nhận đánh giá và xem tổng kết.

Ta được biểu đồ use case tổng quan hệ thống tuyển dụng HireLens:

## Truy vết nguồn

| Nội dung | Nguồn |
|---|---|
| Actor, bảo vệ route và trang công khai | `source/recruit_system/frontend/src/App.tsx:22`, `source/recruit_system/frontend/src/App.tsx:39`, `source/recruit_system/frontend/src/App.tsx:50` |
| Đăng ký, đăng nhập, chọn vai trò | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:32`, `source/recruit_system/frontend/src/pages/LoginPage.tsx:32`, `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:25` |
| Danh sách công khai, chuyển đăng ký khi khách chọn ứng tuyển | `source/recruit_system/frontend/src/pages/PublicHomePage.tsx:41`, `source/recruit_system/frontend/src/pages/PublicHomePage.tsx:77` |
| CV | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:122`, `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:139` |
| Đối sánh và xem chi tiết | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:30`, `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:139`, `source/recruit_system/frontend/src/pages/recruiter/RecruiterMatchingPage.tsx:48` |
| Ứng tuyển tại trang chủ | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:91`, `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:212` |
| Ôn tập và chấm phỏng vấn | `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:31`, `source/recruit_system/frontend/src/pages/candidate/CandidateInterviewPage.tsx:40`, `source/recruit_system/docs/Module3_Interview_Flow.md:47` |

**Điểm cần xác nhận:** Không có.
