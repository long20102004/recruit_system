# M2-CLS-BE — Tải lên CV PDF, kiểm tra và xác nhận các trường hồ sơ

## Phạm vi và luồng chính

Biểu đồ thể hiện hai yêu cầu POST và PUT của M2-ACT trong recruitment-service; không vẽ frontend hoặc nội bộ dịch vụ AI/identity. Các package View, Controller, Model là nhóm thiết kế; View chứa DTO HTTP, không phải trang render phía server. Có 18 lớp/interface, chỉ chọn thành viên được dùng trong luồng; `save`, `deleteAll`, `flush` là phương thức kế thừa Spring Data, không khai báo lại trong interface con. `SecurityUtils`, `UserPrincipal`, `AppProperties`, ngoại lệ và các kiểu thư viện không vẽ để giữ giới hạn.

1. `CvController.upload` chuyển file tới `CvService.upload`; service kiểm tra vai trò, hồ sơ, tệp, gọi `CvExtractionModule.extract`. Module tạo `PdfTextExtractor`, kiểm tra nội dung, rồi gọi `AiJsonClient.post` tới AI. Sau khi nhận dữ liệu, service lưu tệp, ghi metadata và ánh xạ trường nhờ `CvProfileMapper.fields`; các trường được lọc theo `SettingService.cvFields` trước khi ghi qua `CvDataRepository`. Cuối cùng service tạo `CvFormResponse` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:22`, `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:53`, `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:18`).
2. `CvController.confirm` chuyển `ConfirmCvRequest` tới `CvService.confirm`. Service kiểm tra đã tải file và danh sách trường được phép, thay các dòng CV, rồi `syncProfile`: tên và điện thoại được gửi qua `IdentityClient.update` → `ServiceHttpClient.patch`; tóm tắt được lưu qua `CandidateProfileRepository`. Sau đó service trả `CvFormResponse` (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:86`, `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/client/IdentityClient.java:13`, `source/recruit_system/backend/common/src/main/java/recruit/demo/client/ServiceHttpClient.java:21`).
3. Khi PDF không hợp lệ/quá 10 trang backend trả 400; text dưới 50 ký tự trả 422. Kết quả AI không có object `data` hợp lệ trả 502; ngoại lệ mạng hoặc JSON không đọc được trả 503 (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:20`, `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/client/AiJsonClient.java:21`).

## Vai trò và truy vết phần tử

Tiền tố `R` trong bảng là `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/`; đường dẫn ngoài tiền tố ghi đầy đủ. Các quan hệ cũng có `src` riêng trong JSON.

| Phần tử | Vai trò trong M2 | Nguồn |
|---|---|---|
| View, Controller, Model | Nhóm thiết kế DTO, điều khiển HTTP và xử lý/dữ liệu | `R/dto/CvDtos.java:13`, `R/controller/CvController.java:13`, `R/service/CvService.java:32` |
| CvController | Nhận POST upload và PUT confirm | `R/controller/CvController.java:13` |
| CvService | Điều phối kiểm tra, lưu, đồng bộ và tạo phản hồi | `R/service/CvService.java:32` |
| CvExtractionModule | Kiểm tra text PDF, gọi AI và kiểm tra object `data` | `R/service/cv/CvExtractionModule.java:12` |
| PdfTextExtractor | Trích xuất text PDF, giới hạn số trang | `R/extraction/pdf/PdfTextExtractor.java:24` |
| CvProfileMapper | Ánh xạ JSON hồ sơ AI sang trường CV | `R/service/cv/CvProfileMapper.java:6` |
| AiJsonClient | Gửi JSON tới dịch vụ AI và xử lý HTTP/lỗi | `R/client/AiJsonClient.java:11` |
| IdentityClient | Gửi cập nhật tên/điện thoại tới identity-service | `R/client/IdentityClient.java:6` |
| ServiceHttpClient | Đóng gói PATCH JSON và token liên dịch vụ | `source/recruit_system/backend/common/src/main/java/recruit/demo/client/ServiceHttpClient.java:13` |
| SettingService | Lấy hoặc khởi tạo cấu hình các trường CV | `R/service/SettingService.java:15` |
| CvDataRepository | Truy vấn và lưu các dòng dữ liệu CV | `R/repository/CvDataRepository.java:8` |
| CandidateProfileRepository | Tìm hồ sơ theo user, lưu summary | `R/repository/CandidateProfileRepository.java:8` |
| SettingRepository | Tìm/lưu cấu hình `CV_FIELD` | `R/repository/SettingRepository.java:8` |
| CvData | Dòng field/value, gồm candidateId | `R/entity/CvData.java:13` |
| CandidateProfile | Hồ sơ ứng viên; `id`, `userId`, `summary` được dùng trong luồng | `R/entity/CandidateProfile.java:19` |
| Setting | Bản ghi cấu hình name/value | `R/entity/Setting.java:13` |
| CvDtos.FieldValue | Một trường và danh sách dòng | `R/dto/CvDtos.java:10` |
| CvDtos.CvFormResponse | Phản hồi tên tệp, trạng thái và các trường | `R/dto/CvDtos.java:13` |
| CvDtos.ConfirmCvRequest | Danh sách trường người dùng xác nhận | `R/dto/CvDtos.java:21` |

`R` là ký hiệu viết tắt trong bảng, không phải thư mục thực tế. Các record Java thể hiện bằng class «dto»; thuộc tính là record component, accessor được compiler sinh. `CandidateProfile` và `CvData` chỉ nối logic bằng `candidateId`, không có tham chiếu đối tượng JPA nên không vẽ association hoặc composition (`R/entity/CvData.java:19`).

## Pattern có trong source

- **Repository / Spring Data:** `CvDataRepository`, `CandidateProfileRepository`, `SettingRepository` mở rộng `JpaRepository` và cung cấp truy vấn theo tên; `CvService` và `SettingService` sử dụng chúng (`R/repository/CvDataRepository.java:8`, `R/repository/CandidateProfileRepository.java:8`, `R/repository/SettingRepository.java:8`, `R/service/CvService.java:158`). Nhờ vậy luồng M2 thao tác từng dòng CV và tìm cấu hình mà không trộn SQL vào bộ điều phối.
- **DTO:** ba record lồng trong `CvDtos` làm hợp đồng dữ liệu giữa controller và client, trong khi `CvData` là dữ liệu lưu trữ (`R/dto/CvDtos.java:10`, `R/controller/CvController.java:23`, `R/entity/CvData.java:13`). Điều này cho phép trả danh sách các trường có cấu trúc mà không phơi bày trực tiếp từng dòng entity và ID CSDL.
- **Dependency Injection qua constructor:** `CvController` và `CvService` dùng Lombok `@RequiredArgsConstructor` với các dependency `final`; `CvExtractionModule` và `IdentityClient` khai báo constructor tường minh (`R/controller/CvController.java:12`, `R/service/CvService.java:30`, `R/service/cv/CvExtractionModule.java:15`, `R/client/IdentityClient.java:9`). Việc thay thế client/repository khi kiểm thử các nhánh AI hoặc đồng bộ identity thuận tiện hơn; riêng `PdfTextExtractor` được tạo bằng `new`, không phải dependency được inject (`R/service/cv/CvExtractionModule.java:20`).

## Mâu thuẫn và giới hạn

- `schema.dbml` khai báo `Ref: cv_data.candidate_id > candidate_profiles.id` (`source/recruit_system/docs/schema.dbml:285`); migration tạo `cv_data` không khai báo foreign key (`source/recruit_system/backend/recruitment-service/src/main/resources/db/migration/V4__cv_data.sql:10`), entity chỉ chứa `Integer candidateId`. Vì thế không suy diễn ràng buộc FK hay association đối tượng.
- M2-ACT gộp 502/503/timeout hoặc kết quả rỗng vào một nhánh; chi tiết là AI trả HTTP 503 cũng bị `AiJsonClient` đổi thành 502, còn timeout/lỗi kết nối hoặc lỗi đọc JSON thành 503, và object `data` rỗng thành 502 (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/client/AiJsonClient.java:21`, `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:25`). Không mặc định mọi HTTP lỗi từ AI là 502: 413 được giữ riêng.
- Ghi chú M2-ACT nói backend không lưu dữ liệu hỏng khi AI lỗi; source đúng là gọi AI trước ghi tệp/CSDL, nhưng không đảm bảo tính nguyên tử chung giữa file, giao dịch CSDL và cập nhật identity về sau (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:63`, `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:104`).
- Tài liệu `Module3_Interview_Flow.md` đặc tả phỏng vấn, không mô tả M2; PDF báo cáo không có trên đĩa nên không đối chiếu được. Kiến trúc microservices theo source, không giả định backend/CSDL đơn khối.

## Cần xác nhận

- Có dự định bổ sung OCR cho PDF thiếu text layer hay duy trì phản hồi 422 hiện tại?
