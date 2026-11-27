# Tasks · 007 Nhiều CV

## Phase 1 · Dữ liệu (backend)
- [x] T001 Migration `V10__multi_cv.sql`: bảng `cv_documents`, cột `cv_data.cv_id`, backfill 1 CV chính cho mỗi ứng viên
- [x] T002 Entity `CvDocument`, thêm `cvId` vào `CvData`; `CvDocumentRepository`
- [x] T003 `CvDataRepository`: query theo CV chính cho các method cũ, thêm method theo `cvId`

## Phase 2 · Service + API (backend)
- [x] T004 `CvServiceImpl` làm việc theo `cvId`: GET/PUT có `cvId`, POST cũ ghi vào CV chính
- [x] T005 Danh sách, thêm CV (giới hạn 5), tải lại file, đổi tên, đặt CV chính, xoá, tải file gốc
- [x] T006 `CvController` + DTO `CvDocumentDto`, `CvUploadResponse`, `RenameCvRequest`
- [x] T007 `ApplicationServiceImpl`: kiểm tra và lưu `cv_id` khi ứng tuyển; chi tiết đơn / file CV theo `cv_id`
- [x] T008 Test service (`CvServiceImplTest`, cập nhật test ứng tuyển nếu có)

## Phase 3 · Frontend [P] (chạy song song với Phase 2, theo contract trong plan)
- [x] T009 `client.ts`: `cvsApi` thêm `cvId`, API documents, type `CvDocumentDto`
- [x] T010 `CandidateCvListPage` dùng API thật, bỏ `cvsMock`
- [x] T011 `CandidateCvPage` hỗ trợ `?cvId=` và `?new=1`
- [x] T012 `ApplyModal` chọn CV gửi kèm

## Phase 4 · Kiểm chứng
- [x] T013 `mvn test`, `npm run lint && npm run build`, review diff

## Kết quả kiểm chứng (2026-11-27)
- `mvn -pl recruitment-service -am test` (JDK 21): 72 test pass, `CvMatchLiveContractTest` skip. JDK 25 mặc định của máy vỡ Lombok, không liên quan feature này.
- Chạy V10 trên bản sao DB dev (`multicv_scratch`, đã xoá sau khi kiểm tra): 3 ứng viên → 3 CV chính, 87/87 dòng `cv_data` có `cv_id`. Service khởi động được (Hibernate validate, JPQL hợp lệ).
- FE: `npm run build` ok; `npm run lint` không có cảnh báo mới ở các file đã sửa.

## Còn mở
- Xoá CV cuối cùng: cvmatch vẫn giữ bản CV cũ của ứng viên (không có sự kiện xoá). Phía ứng viên không bị ảnh hưởng vì gợi ý việc yêu cầu CV chính.
- Ngữ cảnh phỏng vấn (`InternalRecruitmentController`) và điểm match của đơn vẫn lấy theo CV chính, không theo CV đã gửi kèm đơn.
- Chưa test thủ công trên UI.
