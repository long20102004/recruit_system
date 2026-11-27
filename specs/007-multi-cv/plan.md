# Plan · 007 Nhiều CV

## Thiết kế

- Bảng `cv_documents` giữ thông tin CV (tên, cờ chính). Nội dung vẫn nằm trong `cv_data` (field/value) như cũ, thêm `cv_id`. Tên file, đường dẫn file, trạng thái, JSON trích xuất vẫn là các field `file_name`, `file_url`, `parsing_status`, `extracted_profile`.
- `CvDataRepository.findByCandidateIdAndFieldOrderByIdAsc` và `findByFieldAndValue` đổi sang query JPQL chỉ lấy dòng của CV chính. Các nơi gọi (matching, cvmatch, phỏng vấn, đơn ứng tuyển) không phải sửa mà tự dùng CV chính (FR-002).
- Thêm `findByCvIdAndFieldOrderByIdAsc` cho thao tác trên một CV cụ thể.
- Ràng buộc "đúng 1 CV chính" giữ ở tầng service, trong transaction.
- cvmatch giữ nguyên khoá theo ứng viên. Đổi CV chính thì nội dung đổi, `content_hash` đổi, nên cvmatch tự gửi lại.

## Contract API (recruitment-service, quyền `cv:manage-own`)

| Method | Path | Body / query | Trả về |
|---|---|---|---|
| GET | `/api/cvs` | `?cvId=` tuỳ chọn, mặc định CV chính | `CvFormResponse` (thêm `cvId`, `title`, `main`) |
| POST | `/api/cvs` | multipart `file` (API cũ: ghi vào CV chính, chưa có thì tạo) | `BaseResponse<CandidateProfileDto>` (giữ nguyên) |
| PUT | `/api/cvs` | `?cvId=` tuỳ chọn; `ConfirmCvRequest` | `CvFormResponse` |
| GET | `/api/cvs/documents` | | `CvDocumentDto[]`, CV chính đứng đầu, còn lại theo `updatedAt` giảm dần |
| POST | `/api/cvs/documents` | multipart `file`, `title` tuỳ chọn | `BaseResponse<CvUploadResponse{cvId, profile}>`; đủ 5 CV trả 400 |
| POST | `/api/cvs/documents/{id}/file` | multipart `file` (tải lại file cho CV này) | `BaseResponse<CvUploadResponse>` |
| PATCH | `/api/cvs/documents/{id}` | `{ "title": "..." }` (1–120 ký tự) | `CvDocumentDto` |
| POST | `/api/cvs/documents/{id}/main` | | `CvDocumentDto[]` |
| DELETE | `/api/cvs/documents/{id}` | | 204; 409 nếu đang trong đơn chưa kết thúc |
| GET | `/api/cvs/documents/{id}/file` | | file PDF gốc |

`CvDocumentDto`: `id, title, fileName, main, parsingStatus, analyzed, skills[], updatedAt, inActiveApplication`. `title` trống thì lấy tên file bỏ đuôi.

Ứng tuyển: `POST /api/applications/jobs/{jobId}` body `{cvDocumentId?, coverLetter?}` (không đổi shape, nay mới thực sự dùng `cvDocumentId`).

## File ảnh hưởng

Backend (`backend/recruitment-service`): migration V10, entity `CvDocument` + `CvData.cvId`, repo `CvDocumentRepository`, `CvDataRepository`, `JobApplicationRepository`; `CvService`/`CvServiceImpl`, `CvController`, DTO mới; `ApplicationServiceImpl` (apply, chi tiết đơn, file CV).

Frontend: `api/client.ts`, `CandidateCvListPage.tsx`, `CandidateCvPage.tsx`, `ApplyModal.tsx`, bỏ `cvsMock` trong `candidateMock.ts`.

## Kiểm chứng

- `mvn -pl recruitment-service -am test` (test service mới cho giới hạn 5 CV, đặt CV chính, xoá CV đang ứng tuyển, ứng tuyển bằng CV không thuộc mình).
- FE: `npm run lint`, `npm run build`.
- Chạy migration trên DB thật (nếu có docker) để kiểm tra backfill.
