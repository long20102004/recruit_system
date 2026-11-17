# M1-CLS-FE — Biểu đồ lớp chi tiết phía Frontend

## Vai trò lớp và luồng gọi

- `RegisterPage`, `LoginPage`, `ChooseRolePage` là các boundary function component; giữ các input/state cần thiết và handler `onSubmit`. Chúng dùng `useAuth` để gọi luồng nghiệp vụ, `useToast` để báo kết quả và điều hướng theo kết quả `accountPath`.
- `RoleOption` là boundary UI được `ChooseRolePage` render cho hai lựa chọn vai trò.
- `AuthProvider` cung cấp trạng thái phiên và các thao tác `login`, `register`, `chooseRole`, `logout`. Khi khởi tạo, provider đọc token, gọi `authApi.me()` để phục hồi user; các thao tác xác thực lưu token và cập nhật user.
- `ToastProvider` quản lý thông báo ngắn hạn; các page gọi `toast` cho thành công/lỗi.
- `authApi` là client phía FE: `login`, `register`, `me`, `chooseRole` gọi API chung; `ApiError` đại diện cho HTTP lỗi. `AuthResponse`, `UserDto`, `RegisterBody`, `RoleDto` là kiểu dữ liệu trao đổi.

Luồng chính: page gọi handler → AuthProvider → authApi → API `/auth/register`, `/auth/login` hoặc `/auth/role` → provider cập nhật token/user → page hiện toast và điều hướng; `ChooseRolePage` dùng `RoleOption` để chọn `CANDIDATE` hoặc `RECRUITER`.

## Pattern thực sự có trong code

- **Context/Provider:** `AuthContext`/`AuthProvider` (`frontend/src/context/AuthContext.tsx:19-30,44-101`) chia sẻ user/loading và các hành động xác thực; `ToastContext`/`ToastProvider` (`frontend/src/context/ToastContext.tsx:11-33`) chia sẻ toast. Cụ thể, ba màn hình M1 tiêu thụ cùng một phiên cập nhật nhất quán thay vì truyền callback và trạng thái qua nhiều cấp component.
- **API client/facade function collection:** hàm `api` tập trung headers, Bearer token, parse lỗi và response (`frontend/src/api/client.ts:32-49`); object `authApi` gom endpoint xác thực (`:51-68`). Nhờ vậy các màn hình/provider không tự lặp fetch, gắn token hay xử lý lỗi HTTP.
- **DTO:** `RegisterBody`, `AuthResponse`, `UserDto`, `RoleDto` (`frontend/src/api/client.ts:151-169`) định hình dữ liệu gửi/nhận của luồng M1; giúp chữ ký gọi API và dữ liệu phiên có cấu trúc rõ ràng.
- **Dependency injection qua React Context (nhẹ):** `useAuth`/`useToast` lấy dependencies từ Context (`frontend/src/context/AuthContext.tsx:104-108`; `frontend/src/context/ToastContext.tsx:35-41`). Các page không khởi tạo client hoặc provider riêng; lợi ích cụ thể là cùng dùng cấu hình client và trạng thái toàn cục.

## Bảng truy vết

| Phần tử | Nguồn |
|---|---|
| RegisterPage, onSubmit, state | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:17-39` |
| LoginPage, onSubmit, state | `source/recruit_system/frontend/src/pages/LoginPage.tsx:17-39` |
| ChooseRolePage, onSubmit, state | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:17-39` |
| RoleOption | `source/recruit_system/frontend/src/components/common/RoleOption.tsx:4-27` |
| AuthProvider operations/state | `source/recruit_system/frontend/src/context/AuthContext.tsx:44-85` |
| ToastProvider/toast | `source/recruit_system/frontend/src/context/ToastContext.tsx:17-33` |
| authApi | `source/recruit_system/frontend/src/api/client.ts:51-68` |
| DTO và RoleDto | `source/recruit_system/frontend/src/api/client.ts:151-169` |
| ApiError | `source/recruit_system/frontend/src/api/client.ts:14-21` |

## Mâu thuẫn và giới hạn

- Không thấy mâu thuẫn giữa tài liệu M1 đã đọc và source FE. `Module3_Interview_Flow.md` nói về phỏng vấn (M4), không mô tả luồng M1; PDF báo cáo chưa có trên đĩa nên không đối chiếu được.
- Activity M1-ACT bỏ luồng phục hồi phiên vì giới hạn node, trong khi `AuthProvider` thực sự gọi `authApi.me()` khi khởi động (`AuthContext.tsx:48-59`). Đã giữ API `me` trong lớp vì yêu cầu biểu diễn những phương thức thật sự được gọi; cần xác nhận phạm vi này.
- React component/provider là function, được mô hình hóa thành class theo quy ước đề bài. Không đưa các component layout/field tổng quát vào vì chúng chỉ dựng giao diện, không tham gia xử lý nghiệp vụ M1.
