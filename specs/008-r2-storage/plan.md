# Plan · 008 Lưu file trên R2

## Thiết kế

- R2 dùng API tương thích S3 → thêm **AWS SDK v2 `s3`** vào recruitment-service. Endpoint
  `https://<accountId>.r2.cloudflarestorage.com`, region `auto`. Đặt checksum `WHEN_REQUIRED`
  (SDK ≥ 2.30 mặc định gửi CRC mà R2 chưa hỗ trợ đầy đủ).
- Package mới `recruit.demo.storage` (chỉ trong recruitment-service, service khác chưa cần):
  - `R2Properties` (`storage.r2.*`, `@Validated`, thiếu giá trị bắt buộc thì lỗi lúc khởi động — FR-007).
  - `StorageService`: `putPrivate`, `putPublic`, `presignGet(key, fileName, inline)`, `publicUrl(key)`,
    `deletePrivate`, `deletePublic`. Cài đặt `R2StorageService` dùng `S3Client` + `S3Presigner`.
  - `ObjectKeys`: sinh key, nhận biết giá trị DB cũ là đường dẫn local (`isLegacyPath`).
- Object key:
  - private: `cvs/{candidateId}/{cvId}/{uuid}.pdf`, `companies/{companyId}/license/{uuid}.{ext}`
  - public: `companies/{companyId}/logo/{uuid}.{ext}`, `companies/{companyId}/cover/{uuid}.{ext}`
- DB:
  - `cv_data` field `file_url` và `companies.license_file_url`: giữ cột, giá trị đổi sang object key.
  - Migration `V11__r2_storage.sql`: `companies.logo_key`, `companies.cover_key` (VARCHAR 512).
- Migrate file cũ: `LegacyFileMigrationRunner` (`ApplicationRunner`) chỉ chạy khi `storage.migrate-local=true`.
  Duyệt `file_url` / `license_file_url` còn là đường dẫn local, đọc file, upload lên bucket private,
  ghi key. Chạy lại an toàn (FR-008). Log số file chuyển / thiếu / lỗi, không log nội dung.
- DTO mới viết dạng class Lombok (không dùng record): `FileLinkDto{url, expiresAt}`.

## Contract API (recruitment-service)

| Method | Path | Trước | Sau |
|---|---|---|---|
| GET | `/api/cvs/documents/{id}/file` | nội dung PDF | `BaseResponse<FileLinkDto>` (attachment, tên file gốc) |
| GET | `/api/applications/{id}/cv-file` | nội dung PDF | `BaseResponse<FileLinkDto>` (attachment) |
| GET | `/api/admin/companies/{id}/license` | nội dung PDF (inline) | `BaseResponse<FileLinkDto>` (inline) |
| POST | `/api/recruiter/company/files?kind=logo\|cover\|license` | ghi đĩa | ghi R2; logo/cover kiểm tra loại ảnh, ≤ 5MB |
| GET | hồ sơ công ty (nhà tuyển dụng + công khai) | `logoFileName` | thêm `logoUrl`, `coverUrl` (null nếu chưa có) |

Quyền giữ nguyên các `@PreAuthorize` / `ensureCanAccess` hiện có.

## Cấu hình (biến môi trường, không commit giá trị thật)

| Biến | Ý nghĩa |
|---|---|
| `R2_ACCOUNT_ID` | Cloudflare account id |
| `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` | API token R2 (quyền Object Read & Write cho 2 bucket) |
| `R2_PRIVATE_BUCKET` | bucket CV, giấy phép |
| `R2_PUBLIC_BUCKET` | bucket ảnh, đã bật public access |
| `R2_PUBLIC_BASE_URL` | vd `https://pub-xxxx.r2.dev` hoặc custom domain |
| `R2_PRESIGN_TTL` | mặc định `5m` |
| `STORAGE_MIGRATE_LOCAL` | `true` để chạy migrate file cũ khi khởi động |

Thêm vào `docker-compose.yml` (recruitment-service) và `.env.microservices.example`.
Volume `recruitment_uploads` giữ lại tới khi migrate xong (là nguồn đọc file cũ).

## File ảnh hưởng

Backend (`backend/recruitment-service`): `pom.xml`, `application.yml`, package `storage`, migration V11,
`Company` entity, `CvServiceImpl`, `ApplicationServiceImpl`, `CompanyServiceImpl`, `CompanyService`,
`CvService`, `ApplicationService`, 3 controller (`CvController`, `ApplicationsController`, `AdminCompanyController`),
`CompanyDtos`, DTO `FileLinkDto`.

Frontend: `api/client.ts` (hàm tải file), `RecruiterApplicationDetailPage.tsx`, `AdminCompaniesPage.tsx`,
`RecruiterCompanyPage.tsx`, trang công ty công khai (hiển thị logo/ảnh bìa).

Hạ tầng: `docker-compose.yml`, `.env.microservices.example`, hướng dẫn tạo bucket trong `docs/R2_STORAGE.md`.

## Kiểm chứng

- `mvn -pl recruitment-service -am test`: test `R2StorageService` (presign offline với key giả: host, bucket,
  hết hạn, `response-content-disposition`), `ObjectKeys`, service CV/công ty với `StorageService` mock,
  runner migrate với file tạm + storage mock.
- FE: `npm run lint`, `npm run build`.
- Thử thật với bucket R2 khi có key (upload CV, tải CV, logo hiển thị, migrate). Không có key thì ghi rõ chưa kiểm.
