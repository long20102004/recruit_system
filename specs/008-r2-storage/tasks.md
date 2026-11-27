# Tasks · 008 Lưu file trên R2

## Phase 1 · Nền tảng storage (backend)
- [x] T001 `pom.xml`: AWS SDK v2 `s3` (BOM); `application.yml`: `storage.r2.*`, `storage.migrate-local`
- [x] T002 `R2Properties`, `StorageService`, `R2StorageService` (S3Client + S3Presigner, checksum WHEN_REQUIRED), `ObjectKeys`
- [x] T003 `FileLinkDto` (class Lombok); test `R2StorageServiceTest`, `ObjectKeysTest`

## Phase 2 · Dùng storage trong nghiệp vụ (backend)
- [x] T004 `CvServiceImpl`: upload CV lên bucket private, `file(cvId)` trả `FileLinkDto`, xoá object khi xoá CV
- [x] T005 `ApplicationServiceImpl.loadCvFile` → link ký tạm; `hasCvFile` không đổi
- [x] T006 `CompanyServiceImpl`: license lên private, logo/cover lên public (kiểm tra ảnh ≤ 5MB); migration `V11__r2_storage.sql`, `Company.logoKey/coverKey`; DTO thêm `logoUrl`, `coverUrl`; link giấy phép cho admin
- [x] T007 3 controller trả `BaseResponse<FileLinkDto>`
- [x] T008 `LegacyFileMigrationRunner` (`storage.migrate-local=true`)
- [x] T009 Cập nhật/thêm test service (CV, công ty, ứng tuyển, migrate) với storage mock

## Phase 3 · Frontend [P] (theo contract trong plan)
- [x] T010 `client.ts`: API lấy link (`FileLinkDto`), helper mở/tải link; `cvsApi.download`
- [x] T011 `RecruiterApplicationDetailPage`, `AdminCompaniesPage` dùng link thay vì blob
- [x] T012 `RecruiterCompanyPage` + trang công ty công khai hiển thị `logoUrl`, `coverUrl`

## Phase 4 · Hạ tầng + kiểm chứng
- [x] T013 `docker-compose.yml`, `.env.microservices.example`, `docs/R2_STORAGE.md` (tạo bucket, token, public access, migrate)
- [x] T014 `mvn -pl recruitment-service -am test`, `npm run lint && npm run build`, review diff

## Kết quả kiểm chứng (2026-11-27)
- `mvn -pl recruitment-service -am test` (JDK 21; JDK 25 mặc định của máy vỡ Lombok): 91 test pass, 1 skip (`CvMatchLiveContractTest`).
  Test mới: `R2StorageServiceTest` (presign offline), `ObjectKeysTest`, `R2PropertiesValidationTest` (FR-007),
  `LegacyFileMigrationRunnerTest`, thêm case R2 trong `CvServiceImplTest`, `CompanyServiceImplTest`.
- FE: `tsc --noEmit` sạch, `npm run lint` không có lỗi (chỉ cảnh báo `set-state-in-effect` có sẵn), `npm run build` OK.
- `docker compose config` hợp lệ.
- `R2LiveSmokeTest` với bucket thật (`hirelens-private`, `hirelens`): upload private, tải qua presigned URL (đúng nội dung,
  `Content-Disposition: attachment`), truy cập không ký bị chặn, upload public và đọc qua URL r2.dev, xoá object: pass.
- **Chưa kiểm**: luồng end-to-end qua app (upload CV trên giao diện, hiển thị logo), migrate file cũ, migration V11 trên MySQL.

## Ghi chú triển khai
- Frontend trước đây chưa gọi `POST /api/recruiter/company/files` (chọn logo/giấy phép chỉ lưu tên file);
  nay upload ngay khi chọn file ở trang đăng ký công ty và trang hồ sơ công ty.
