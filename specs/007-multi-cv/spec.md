# 007 · Nhiều CV cho mỗi ứng viên (màn C02, C05)

Nguồn: `docs/MISSING_FEATURES.md` mục 8 (F1-02). Route FE: `/candidate/cvs` (danh sách), `/candidate/cv?cvId=` (sửa một CV), modal ứng tuyển.

Ngoài phạm vi:
- "Tạo CV từ đầu" bằng form (F1-04, phụ thuộc mẫu CV của tính năng 14). Nút vẫn giữ như cũ.
- % phù hợp của **từng** CV khi ứng tuyển. cvmatch đang index 1 CV cho mỗi ứng viên (`match_cv_link` khoá theo `candidate_id`), nên chỉ CV chính có điểm. Muốn có điểm cho từng CV phải đổi luồng đồng bộ cvmatch (module M2), để làm sau.

## User stories

- **US1. Danh sách CV.** Ứng viên xem tối đa 5 CV: tên, tên file, kỹ năng, ngày cập nhật, CV nào là CV chính, CV nào đang gắn với đơn ứng tuyển chưa kết thúc.
- **US2. Thêm CV.** Tải thêm một CV PDF. AI trích xuất, ứng viên sửa rồi lưu như luồng CV hiện tại. CV đầu tiên tự thành CV chính. Đã đủ 5 CV thì báo lỗi.
- **US3. Quản lý CV.** Sửa nội dung, đổi tên, đặt làm CV chính, tải file gốc, xoá.
- **US4. Ứng tuyển bằng CV đã chọn.** Khi ứng tuyển, ứng viên chọn CV gửi kèm (mặc định CV chính). Nhà tuyển dụng xem đúng CV đã gửi.

## Yêu cầu

| Mã | Nội dung |
|---|---|
| FR-001 | Mỗi ứng viên có tối đa 5 CV, đúng 1 CV chính khi có ít nhất 1 CV. Vượt 5 trả 400. |
| FR-002 | CV chính là nguồn dữ liệu cho matching, gợi ý việc, đồng bộ cvmatch và phỏng vấn. Mọi chỗ đang đọc CV theo ứng viên đều đọc CV chính. |
| FR-003 | Đổi CV chính, hoặc sửa / tải lại CV chính, phát sự kiện `CvChanged` để đồng bộ lại cvmatch. Sửa CV phụ thì không. |
| FR-004 | Chỉ khi lưu CV chính mới đồng bộ họ tên, SĐT sang identity và tóm tắt sang `candidate_profiles`. |
| FR-005 | Không xoá được CV đang gắn với đơn ở trạng thái `SUBMITTED`, `REVIEWING`, `INTERVIEW` (409). Xoá CV chính thì CV cập nhật gần nhất còn lại thành CV chính. |
| FR-006 | Ứng viên chỉ thao tác trên CV của mình. CV của người khác trả 404. |
| FR-007 | Ứng tuyển: `cvDocumentId` phải là CV đã trích xuất xong của ứng viên (sai thì 400). Bỏ trống thì dùng CV chính. Đơn lưu `cv_id`. |
| FR-008 | Chi tiết đơn và tải file CV phía nhà tuyển dụng dùng CV đã gắn với đơn. Đơn cũ chưa có `cv_id` dùng CV chính. |
| FR-009 | API cũ `GET/POST/PUT /api/cvs` vẫn chạy (không truyền `cvId` thì làm trên CV chính; POST khi chưa có CV thì tạo CV đầu tiên). |

## Dữ liệu

Migration `V10__multi_cv.sql`: bảng mới `cv_documents(id, candidate_id, title, is_main, created_at, updated_at)`. `cv_data` thêm cột `cv_id`. Dữ liệu cũ: mỗi ứng viên đã có `cv_data` được tạo 1 CV chính và gắn toàn bộ dòng cũ vào CV đó.

## Tiêu chí nghiệm thu

- Ứng viên có 1 CV cũ sau migration vẫn thấy CV đó (là CV chính), matching không đổi.
- Thêm CV thứ 2, đặt làm chính → gợi ý việc dùng CV mới.
- Ứng tuyển bằng CV phụ → nhà tuyển dụng mở đơn thấy file và nội dung của CV phụ.
- Xoá CV đang trong đơn `SUBMITTED` bị từ chối.
