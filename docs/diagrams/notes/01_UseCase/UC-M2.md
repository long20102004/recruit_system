# UC-M2 — Tải lên và xác nhận CV

## Bước 1. Sao chép use case và actor liên quan
Actor là Ứng viên, tương tác với chức năng chính Tải lên và xác nhận CV trên trang `CandidateCvPage.tsx`.

## Bước 2. Xác định các use case chi tiết theo giao diện
Trang `CandidateCvPage.tsx` chứa các bước tải CV, kiểm tra/chỉnh sửa trường hồ sơ và xác nhận; đây là các giao diện của cùng một trang, không phải các route hoặc hộp thoại độc lập. Sau khi xác nhận, trang hiển thị hồ sơ đã xác nhận. Nút “Cập nhật hồ sơ” cho phép tùy chọn quay lại bước chỉnh sửa.

## Bước 3. Xác định quan hệ với use case chính
Tải CV PDF và trích xuất thông tin, kiểm tra và chỉnh sửa thông tin CV, và xác nhận hồ sơ CV được mô hình hóa bằng quan hệ `<<include>>` vì là các bước trong luồng hoàn tất chức năng. Cập nhật hồ sơ đã xác nhận là tùy chọn, dùng `<<extend>>` tại extension point “Cập nhật hồ sơ sau khi xác nhận”.

## Bước 4. Mô tả các use case
- **Tải lên và xác nhận CV:** cho phép ứng viên tải CV PDF, kiểm tra/chỉnh sửa dữ liệu trích xuất và xác nhận hồ sơ.
- **Tải CV PDF và trích xuất thông tin:** cho phép ứng viên chọn CV PDF; hệ thống tải lên và trả về các trường trích xuất.
- **Kiểm tra và chỉnh sửa thông tin CV:** cho phép ứng viên rà soát, chỉnh sửa các trường hồ sơ trước khi xác nhận.
- **Xác nhận hồ sơ CV:** cho phép ứng viên gửi các trường hồ sơ đã kiểm tra để lưu xác nhận.
- **Cập nhật hồ sơ đã xác nhận:** cho phép ứng viên tùy chọn quay lại bước chỉnh sửa hồ sơ.

Ta được biểu đồ use case chi tiết chức năng “Tải lên và xác nhận CV”:

### Truy vết
| Phần tử/quan hệ | Nguồn |
|---|---|
| Actor, chức năng chính, trang CV | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:94` |
| Tải lên CV | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:122`; `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:22` |
| Kiểm tra/chỉnh sửa trường | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:271` |
| Xác nhận | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:139`; `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:27` |
| Cập nhật hồ sơ (tùy chọn) | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:213` |
