# ST-M1 — Biểu đồ trạng thái chức năng đăng ký, đăng nhập và chọn vai trò

**Bước 1.** Căn cứ kịch bản chuẩn và ngoại lệ M1 (`KB-M1.md`), use case chi tiết `UC-M1.json` và các trang frontend thực tế, xác định các giao diện chính và thông báo trong chu trình xác thực tài khoản:
- Giao diện Trang đăng ký (`RegisterPage.tsx` tại route `/register`): cho phép nhập email, mật khẩu để tạo tài khoản mới.
- Giao diện Trang đăng nhập (`LoginPage.tsx` tại route `/login`): cho phép nhập email, mật khẩu đã có để xác thực.
- Giao diện Trang chọn vai trò (`ChooseRolePage.tsx` tại route `/choose-role`): hiển thị lựa chọn vai trò Ứng viên hoặc Nhà tuyển dụng cho tài khoản chưa phân định vai trò lần đầu (`roleChosen = false`).
- Giao diện Trang chủ ứng viên (`CandidateHomePage.tsx` tại route `/candidate`): không gian làm việc sau khi đăng nhập hoặc chọn vai trò Ứng viên.
- Giao diện Trang chủ nhà tuyển dụng (`RecruiterHomePage.tsx` tại route `/recruiter`): không gian làm việc sau khi đăng nhập hoặc chọn vai trò Nhà tuyển dụng.
- Các trạng thái thông báo kết quả (toast notification): Hiện thông báo lỗi đăng ký, Hiện thông báo lỗi đăng nhập, Hiện thông báo lỗi chọn vai trò.

**Bước 2.** Xác định chuyển trạng thái theo thao tác người dùng và kết quả xử lý của các dịch vụ backend:
- Khách truy cập hệ thống bắt đầu từ điểm rẽ nhánh kiểm tra tài khoản, mở giao diện Trang đăng ký hoặc Trang đăng nhập. Người dùng có thể chuyển đổi qua lại giữa hai giao diện này thông qua liên kết chuyển đổi.
- Tại giao diện Trang đăng ký, khi nhấn "Tạo tài khoản", hệ thống gửi yêu cầu đăng ký tới `identity-service`. Nếu email đã tồn tại hoặc vi phạm định dạng thì hiển thị thông báo lỗi; click OK để giữ nguyên giao diện đăng ký và nhập lại. Nếu đăng ký thành công, hệ thống cấp JWT và tự động chuyển tiếp tới giao diện Trang chọn vai trò.
- Tại giao diện Trang đăng nhập, khi nhấn "Đăng nhập", hệ thống gửi yêu cầu xác thực. Nếu sai email/mật khẩu hoặc tài khoản bị khóa thì hiển thị thông báo lỗi; click OK để quay lại giao diện đăng nhập nhập lại. Nếu đăng nhập thành công, hệ thống rẽ nhánh theo trạng thái `roleChosen` và `role`: chuyển sang Trang chọn vai trò nếu chưa chọn vai trò, hoặc điều hướng thẳng tới Trang chủ ứng viên / Trang chủ nhà tuyển dụng tương ứng.
- Tại giao diện Trang chọn vai trò, người dùng chọn vai trò và nhấn "Tiếp tục". Nếu yêu cầu không hợp lệ hoặc vai trò đã được lưu trước đó thì hiển thị thông báo lỗi; click OK để chọn lại. Nếu lưu thành công, hệ thống cấp JWT mới, kích hoạt khởi tạo hồ sơ tự động tại `recruitment-service` và chuyển hướng tới Trang chủ ứng viên hoặc Trang chủ nhà tuyển dụng.
- Tại giao diện Trang chủ ứng viên hoặc Trang chủ nhà tuyển dụng, người dùng có thể đăng xuất để xóa phiên làm việc và quay về Trang đăng nhập, hoặc tiếp tục chuyển sang các chức năng nghiệp vụ khác của hệ thống để kết thúc luồng M1.

Ta được biểu đồ trạng thái chức năng Đăng ký, đăng nhập và chọn vai trò:

- Tại giao diện **Trang đăng ký**, nếu người dùng click *"Đã có tài khoản? Đăng nhập"* thì chuyển sang giao diện **Trang đăng nhập**.
- Tại giao diện **Trang đăng ký**, nếu người dùng nhập email, mật khẩu và click *"Tạo tài khoản"* thì hệ thống gửi yêu cầu đăng ký:
  - Nếu email đã tồn tại hoặc dữ liệu vi phạm định dạng thì chuyển sang trạng thái **Hiện thông báo lỗi đăng ký**; click OK thì giữ nguyên giao diện Trang đăng ký để người dùng chỉnh sửa và nhập lại.
  - Nếu đăng ký hợp lệ và thành công thì hệ thống cấp mã xác thực JWT, thông báo thành công và chuyển sang giao diện **Trang chọn vai trò**.
- Tại giao diện **Trang đăng nhập**, nếu người dùng click *"Chưa có tài khoản? Đăng ký"* thì chuyển sang giao diện **Trang đăng ký**.
- Tại giao diện **Trang đăng nhập**, nếu người dùng nhập email, mật khẩu và click *"Đăng nhập"* thì hệ thống gửi yêu cầu xác thực:
  - Nếu sai thông tin xác thực hoặc tài khoản bị vô hiệu hóa thì chuyển sang trạng thái **Hiện thông báo lỗi đăng nhập**; click OK thì giữ nguyên giao diện Trang đăng nhập để người dùng nhập lại.
  - Nếu đăng nhập thành công và tài khoản chưa chọn vai trò lần đầu (`roleChosen = false`) thì chuyển sang giao diện **Trang chọn vai trò**.
  - Nếu đăng nhập thành công và tài khoản đã chọn vai trò Ứng viên (`role = CANDIDATE`) thì điều hướng sang giao diện **Trang chủ ứng viên**.
  - Nếu đăng nhập thành công và tài khoản đã chọn vai trò Nhà tuyển dụng (`role = RECRUITER`) thì điều hướng sang giao diện **Trang chủ nhà tuyển dụng**.
- Tại giao diện **Trang chọn vai trò**, nếu người dùng chọn vai trò và click *"Tiếp tục"* thì hệ thống gửi yêu cầu lưu vai trò:
  - Nếu vai trò không hợp lệ hoặc đã được lưu trước đó thì chuyển sang trạng thái **Hiện thông báo lỗi chọn vai trò**; click OK thì giữ nguyên giao diện Trang chọn vai trò để người dùng chọn lại.
  - Nếu lưu vai trò thành công với vai trò Ứng viên thì hệ thống cấp JWT mới, tự động khởi tạo hồ sơ ứng viên tại `recruitment-service` và chuyển sang giao diện **Trang chủ ứng viên**.
  - Nếu lưu vai trò thành công với vai trò Nhà tuyển dụng thì hệ thống cấp JWT mới, tự động khởi tạo công ty và hồ sơ nhà tuyển dụng tại `recruitment-service`, sau đó chuyển sang giao diện **Trang chủ nhà tuyển dụng**.
- Tại giao diện **Trang chủ ứng viên**, nếu người dùng click *"Đăng xuất"* thì hệ thống xóa mã JWT và quay về giao diện **Trang đăng nhập**; nếu chuyển sang các chức năng nghiệp vụ khác (tải CV, tìm việc, luyện phỏng vấn) thì kết thúc luồng M1.
- Tại giao diện **Trang chủ nhà tuyển dụng**, nếu người dùng click *"Đăng xuất"* thì hệ thống xóa mã JWT và quay về giao diện **Trang đăng nhập**; nếu chuyển sang các chức năng quản lý tin tuyển dụng và ứng viên thì kết thúc luồng M1.

---

**Truy vết mã nguồn (`src`):**
- Trạng thái bắt đầu và rẽ nhánh truy cập: `source/recruit_system/frontend/src/App.tsx:49-53`
- Giao diện Trang đăng ký và xử lý đăng ký: `source/recruit_system/frontend/src/pages/RegisterPage.tsx:29-85`, `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:28-46`
- Giao diện Trang đăng nhập và xử lý đăng nhập: `source/recruit_system/frontend/src/pages/LoginPage.tsx:29-84`, `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:68-75`
- Giao diện Trang chọn vai trò và xử lý lưu vai trò: `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:28-73`, `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:49-66`
- Điều hướng theo vai trò: `source/recruit_system/frontend/src/utils/account.ts:1-7`
- Giao diện Trang chủ ứng viên: `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:66-100`
- Giao diện Trang chủ nhà tuyển dụng: `source/recruit_system/frontend/src/pages/recruiter/RecruiterHomePage.tsx:28-138`
- Tạo hồ sơ ứng viên và nhà tuyển dụng ngầm: `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/ProfileProvisioningService.java:14-25`
- Thao tác đăng xuất tại thanh điều hướng: `source/recruit_system/frontend/src/components/common/SiteHeader.tsx:30-35`
- Đối chiếu kịch bản: `diagrams/notes/02_KichBan/KB-M1.md` và use case chi tiết `diagrams/specs/01_UseCase/UC-M1.json`.

**Open questions:**
- [cần xác nhận] Vai trò `ADMIN` có trong enum `Role` nhưng chỉ được cấp qua seed CSDL (`V2__seed.sql`); hệ thống không có giao diện đăng ký hoặc chọn vai trò ADMIN trên frontend.
- [cần xác nhận] Luồng khôi phục phiên tự động qua hook `useEffect` (`GET /api/auth/me`) diễn ra ngầm khi mở ứng dụng; nếu token hết hạn (24h) hoặc không hợp lệ, hệ thống tự động xóa token và chuyển hướng về trang công khai `/` hoặc `/login`.
