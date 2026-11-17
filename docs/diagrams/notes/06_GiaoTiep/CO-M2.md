# CO-M2 — Biểu đồ giao tiếp chức năng tải và xác nhận CV

**Bước 1.** Dùng tác nhân Ứng viên và hai lớp biên `CandidateCvProfileView`, `CandidateCvReviewView` đã xác định trong AN-M2. Hai lớp biên là hai chế độ của `CandidateCvPage.tsx`, không phải hai trang/route riêng. Các lớp thực thể trong AN-M2 gồm `CvData`, `CandidateProfile`, `User`.

**Bước 2.** Chuyển luồng chính KB-M2 thành các tương tác tuần tự. Các hàm xử lý dữ liệu chỉ dùng `mine()`, `upload()`, `confirm()` đã có trong AN-M2; trong mô hình pha phân tích, chúng là hàm của lớp chủ thể `CvData`.

## Kịch bản chuẩn V2

1. Ứng viên click “Hồ sơ / CV” để mở `CandidateCvProfileView`.
2. `CandidateCvProfileView` gọi `CvData` để tải hồ sơ.
3. `CvData` thực hiện hàm `mine()`.
4. `CvData` trả kết quả cho `CandidateCvProfileView`.
5. `CandidateCvProfileView` hiển thị hồ sơ cho Ứng viên.
6. Ứng viên click “Cập nhật hồ sơ”.
7. `CandidateCvProfileView` chuyển sang `CandidateCvReviewView` và hiển thị giao diện kiểm tra CV cho Ứng viên.
8. Ứng viên chọn CV PDF tại `CandidateCvReviewView`.
9. `CandidateCvReviewView` gọi `CvData` để tải và phân tích CV.
10. `CvData` thực hiện hàm `upload()`.
11. `CvData` trả kết quả trích xuất cho `CandidateCvReviewView`.
12. `CandidateCvReviewView` hiển thị tên tệp và các trường trích xuất cho Ứng viên kiểm tra.
13. Ứng viên click “Xác nhận hồ sơ”.
14. `CandidateCvReviewView` gọi `CvData` để xác nhận các trường hồ sơ.
15. `CvData` thực hiện hàm `confirm()`.
16. `CvData` trả kết quả xác nhận cho `CandidateCvReviewView`.
17. `CandidateCvReviewView` chuyển về `CandidateCvProfileView` sau khi xác nhận thành công.
18. `CandidateCvProfileView` hiển thị hồ sơ đã xác nhận cho Ứng viên.

## Suy ra biểu đồ

**Bước 3.** Tạo actor và object cho mọi lớp xuất hiện trong mô hình phân tích; đặt stereotype `boundary` cho hai lớp `…View`, stereotype `entity` cho `CvData`, `CandidateProfile`, `User`. Nối các cặp object có trao đổi theo luồng; thao tác thực hiện hàm được thể hiện bằng self-message.

**Bước 4.** Đánh số message từ 1 đến 18, khớp từng bước V2. Nhãn message rút gọn theo quy ước giao tiếp; các hàm giữ đúng tên trong AN-M2.

Ta được biểu đồ giao tiếp pha phân tích chức năng tải và xác nhận CV:

### Ghi chú truy vết

- Actor và thao tác mở khu vực hồ sơ: `source/recruit_system/frontend/src/components/common/SiteHeader.tsx:48`.
- Các trạng thái giao diện, thao tác tải/xác nhận và chuyển chế độ: `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:114`, `:122`, `:139`, `:146`, `:173`, `:214`, `:228`, `:247`, `:281`.
- Chọn tệp: `source/recruit_system/frontend/src/components/common/UploadZone.tsx:21`.
- Các hàm `mine()`, `upload()`, `confirm()`: `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:47`, `:53`, `:86`.
- `CandidateProfile` và `User` được giữ theo AN-M2; `confirm()` đồng bộ dữ liệu hồ sơ trong backend nhưng V2 không đặc tả trao đổi trực tiếp riêng với từng object nên không thêm message suy đoán.

### open_questions

- [cần xác nhận] Đích điều hướng cụ thể khi phiên hết hạn hoặc truy cập sai vai trò và API trả 401/403.
