# AN-M2 — Biểu đồ lớp pha phân tích chức năng tải và xác nhận CV

**Bước 1.** Từ các giao diện chính trong kịch bản, đề xuất hai lớp biên:

- `CandidateCvProfileView`: hiển thị hồ sơ với `outName`, `outContact`, `outFields`; có `subUpdateProfile` và `subViewMatching`. Nguồn: `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:173`.
- `CandidateCvReviewView`: tải và kiểm tra CV với `inFile`, `outFileName`, `outStep`, `inFields`, `subUploadAnother`, `subConfirm`. Nguồn: `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:228`, `source/recruit_system/frontend/src/components/common/UploadZone.tsx:56`.

Đây là hai chế độ của cùng `CandidateCvPage.tsx`, không phải hai trang hay hai route khác nhau. Sau khi chọn cập nhật, trang chuyển sang bước kiểm tra; khi xác nhận thành công, trang chuyển sang chế độ xem hồ sơ. Nút xem việc phù hợp dẫn sang M3, ngoài phạm vi biểu đồ này (`source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:213`, `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:146`).

**Bước 2.** Với các xử lý dữ liệu chính, dùng tên hàm có thật ở `CvService`, phân công chúng cho lớp chủ thể `CvData` trong mô hình phân tích:

- Tên hàm: `mine()`
  - Input: không có tham số tường minh; ứng viên được xác định từ phiên xác thực.
  - Output: `CvFormResponse` gồm tên tệp, trạng thái, cờ phân tích và các trường CV.
  - Lớp chủ thể: `CvData`.
  - Nguồn: `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:47`, `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:123`.

- Tên hàm: `upload()`
  - Input: tệp `MultipartFile`.
  - Output: `CvFormResponse` chứa các trường đã trích xuất; lỗi nếu kiểm tra, trích xuất hoặc lưu thất bại.
  - Lớp chủ thể: `CvData`.
  - Nguồn: `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:53`.

- Tên hàm: `confirm()`
  - Input: `ConfirmCvRequest` chứa các trường và danh sách giá trị ứng viên xác nhận.
  - Output: `CvFormResponse` sau cập nhật; lỗi nếu chưa có tệp hoặc dữ liệu không hợp lệ.
  - Lớp chủ thể: `CvData`.
  - Nguồn: `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:86`.

Ba hàm trên thực tế thuộc service, không phải phương thức khai báo trên entity; việc đặt chúng vào `CvData` chỉ là phân công trách nhiệm trong pha phân tích. `confirm()` còn đồng bộ họ tên không rỗng, điện thoại sang identity-service và tóm tắt vào `CandidateProfile` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:103`). Chỉnh sửa trường và chọn tải tệp khác là thay đổi trạng thái giao diện tại chỗ, không gán thêm hàm nghiệp vụ cho thực thể (`source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:158`, `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:249`).

Giữ các thực thể `CvData`, `CandidateProfile`, `User` cùng thuộc tính không kiểu và quan hệ từ biểu đồ trích lớp thực thể: nhiều `CvData` thuộc một `CandidateProfile`; `CandidateProfile` tham chiếu logic tới `User` qua định danh giữa các service, không khẳng định có khóa ngoại liên service (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/CvData.java:20`, `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/CandidateProfile.java:26`). Lớp biên xem hồ sơ gọi `mine()`; lớp biên kiểm tra gọi `upload()` và `confirm()`.

**Lưu ý:** `upload()` đã ghi trạng thái `COMPLETED`; khi tải lại, cờ `analyzed` có thể đưa giao diện thẳng về chế độ xem, nên trạng thái này không chứng minh một lần xác nhận riêng (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:72`, `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:103`). Giao diện ghi tối đa 5 MB nhưng `UploadZone` không tự kiểm tra kích thước (`source/recruit_system/frontend/src/components/common/UploadZone.tsx:12`).

Ta được biểu đồ lớp pha phân tích chức năng tải và xác nhận CV:

### open_questions

- [cần xác nhận] Đích điều hướng cụ thể khi hết phiên hoặc sai vai trò và API trả 401/403.
