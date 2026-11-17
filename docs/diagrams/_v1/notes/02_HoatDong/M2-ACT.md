# M2-ACT — Tải lên CV PDF, kiểm tra và xác nhận các trường hồ sơ

## Kịch bản chính

1. **N00–N01:** Bắt đầu; ứng viên truy cập trang quản lý CV (`CandidateCvPage`), kéo thả hoặc chọn tệp CV định dạng PDF vào khu vực `UploadZone`.
2. **N02–N04:** Frontend kiểm tra phần mở rộng tệp. Khi tệp có đuôi `.pdf` hợp lệ, Frontend đóng gói tệp vào `FormData` và gửi yêu cầu tải lên qua `POST /api/cvs` (`cvsApi.upload`).
3. **N05–N06:** `recruitment-service` (`CvController.upload` → `CvService.upload`) kiểm tra phân quyền `Role.CANDIDATE` của người dùng hiện tại và xác thực tệp gửi lên không bị rỗng.
4. **N07–N08:** Backend chuyển dữ liệu byte PDF sang `CvExtractionModule`, sử dụng `PdfTextExtractor` để bóc tách văn bản, khôi phục thứ tự đọc theo tọa độ bằng thuật toán Recursive XY-cut; đồng thời xác thực số trang không vượt quá 10 trang và nội dung văn bản đạt tối thiểu 50 ký tự.
5. **N09–N11:** Backend gửi văn bản trích xuất sang dịch vụ AI qua `POST /api/v1/extract-cv?include=kg` (`AiJsonClient`). Tại `cv-extraction-ai`, mô hình ngôn ngữ lớn Qwen GGUF sinh cấu trúc JSON, chạy qua đường ống hậu xử lý (`postprocess`) để căn chỉnh và đối soát văn bản gốc, rồi làm giàu dữ liệu qua Knowledge Graph (`enrich`) để chuẩn hóa trường học và suy diễn kỹ năng ngầm định (`implied_skills`).
6. **N12:** Backend nhận phản hồi JSON hợp lệ từ AI, lưu trữ tệp PDF vật lý vào thư mục cấu hình `app.upload.path`, lưu metadata tệp (`file_name`, `file_url`, `parsing_status = COMPLETED`), ánh xạ các trường qua `CvProfileMapper` và lưu dữ liệu ban đầu vào bảng `cv_data`.
7. **N13:** Frontend nhận đối tượng `CvFormResponse`, kích hoạt chuyển sang Bước 2 (`step = 2`), hiển thị thông báo thành công và kết xuất biểu mẫu gồm danh sách các trường hồ sơ cho phép chỉnh sửa.
8. **N14–N15:** Người dùng rà soát thông tin trích xuất, chỉnh sửa các trường văn bản đơn dòng hoặc đa dòng (Họ tên, Email, Điện thoại, Tóm tắt, Kỹ năng, Kỹ năng suy ra, Học vấn, Kinh nghiệm, Chứng chỉ) và nhấn nút "Xác nhận hồ sơ".
9. **N16–N18:** Frontend kiểm tra điều kiện đã có tệp CV được tải lên (`fileName` hợp lệ); gửi toàn bộ danh sách trường và giá trị đã hiệu chỉnh lên backend qua `PUT /api/cvs` (`cvsApi.confirm`).
10. **N19–N21:** Backend xác thực quyền `Role.CANDIDATE`, đối chiếu tên các trường gửi lên với danh sách cấu hình `CV_FIELD` trong `SettingService`. Sau đó, cập nhật lại các dòng giá trị trong bảng `cv_data`, đồng bộ Họ tên và Số điện thoại sang `identity-service` qua API nội bộ `PATCH /internal/users/{id}`, cập nhật Tóm tắt vào `CandidateProfile`, và ghi nhận trạng thái phân tích `COMPLETED`.
11. **N22:** Frontend nhận phản hồi hồ sơ đã xác nhận, chuyển trạng thái sang Bước 3 (`step = 3`), hiển thị thông báo xác nhận thành công và hiển thị giao diện xem chi tiết "Hồ sơ của bạn" kèm các tùy chọn xem việc làm phù hợp hoặc chỉnh sửa lại.
12. **N25:** Kết thúc luồng hoạt động thành công.

---

## Ngoại lệ

1. **N02 → N03 → N23 → N24 → N25:** Tệp người dùng chọn không có đuôi `.pdf` (`CandidateCvPage.tsx:123`): Frontend từ chối ngay tại giao diện, hiển thị toast "Chỉ nhận file PDF" và dừng luồng tải lên.
2. **N06 → N23 → N24 → N25:** Yêu cầu tải lên bị từ chối tại backend do chưa xác thực (`401 Unauthorized`), sai vai trò (`403 Forbidden`), không tìm thấy hồ sơ ứng viên (`400 Bad Request: Candidate profile not found`), hoặc tệp tải lên bị rỗng (`400 Bad Request: File is required`) (`CvService.java:56, 219`). Frontend bắt lỗi và hiển thị toast thông báo thất bại.
3. **N08 → N23 → N24 → N25:** Tệp PDF vượt quá 10 trang bị từ chối với lỗi `400 Bad Request` ("Invalid PDF or too many pages") (`PdfTextExtractor.java:171`, `CvExtractionModule.java:21`); hoặc tệp PDF dạng ảnh quét thuần túy không có lớp văn bản (< 50 ký tự) bị từ chối với mã lỗi `422 Unprocessable Entity` ("PDF has no readable text; OCR is required for scanned CVs") (`CvExtractionModule.java:23`). Frontend hiển thị thông báo lỗi qua toast.
4. **N11 → N23 → N24 → N25:** Lỗi từ dịch vụ AI trích xuất: mô hình chưa được nạp (`503 Service Unavailable`), văn bản vượt độ dài context (`413 Payload Too Large`), dịch vụ AI trả về lỗi HTTP 4xx/5xx hoặc kết quả rỗng không thể phân tích cú pháp JSON (`502 Bad Gateway`), cuộc gọi bị timeout/ngắt quãng (`503 Service Unavailable`) (`AiJsonClient.java:21-27`, `CvExtractionModule.java:26-27`). Backend không lưu dữ liệu hỏng vào CSDL; Frontend bắt ngoại lệ và toast thông báo lỗi.
5. **N16 → N17 → N23 → N24 → N25:** Người dùng nhấn nút xác nhận khi chưa hoàn tất tải tệp CV lên hệ thống: Frontend kiểm tra biến `fileName` và hiển thị toast nhắc nhở "Hãy tải CV trước" (`CandidateCvPage.tsx:140-141`). Nếu vượt qua kiểm tra ở client, backend kiểm tra lại giá trị `FILE_NAME` trong `cv_data` và trả về lỗi `400 Bad Request` ("Hãy tải CV trước") (`CvService.java:88-90`).
6. **N20 → N23 → N24 → N25:** Dữ liệu xác nhận hồ sơ bị thiếu hoặc chứa trường không nằm trong danh mục cấu hình hệ thống `CV_FIELD`: backend từ chối với `400 Bad Request` ("Thiếu dữ liệu hồ sơ" hoặc "Field không nằm trong cấu hình CV_FIELD: ...") (`CvService.java:93, 101`). Frontend hiển thị thông báo "Xác nhận thất bại".

*Ghi chú về nút N23/N24:* Nút N23 là điểm gộp (merge) các luồng ngoại lệ và lỗi validation từ các tầng (client, server, AI); nút N24 là thao tác hiển thị toast thông báo lỗi cụ thể cho người dùng trước khi kết thúc luồng.

---

## Bảng truy vết node → file:dòng

| Node | Loại | Nội dung | Nguồn truy vết |
|---|---|---|---|
| N00 | initial | Bắt đầu | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:94` |
| N01 | action | Chọn hoặc kéo thả tệp CV PDF vào UploadZone | `source/recruit_system/frontend/src/components/common/UploadZone.tsx:38` |
| N02 | decision | Tệp có định dạng .pdf? | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:123` |
| N03 | action | Hiển thị thông báo chỉ nhận file PDF | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:124` |
| N04 | action | Gửi yêu cầu tải lên CV (POST /api/cvs) | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:129` |
| N05 | action | Kiểm tra quyền CANDIDATE và dữ liệu tệp | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:54` |
| N06 | decision | Quyền và tệp hợp lệ? | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:55` |
| N07 | action | Trích xuất văn bản và kiểm tra số trang PDF | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:20` |
| N08 | decision | PDF hợp lệ và có lớp văn bản? | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:21` |
| N09 | action | Gửi yêu cầu trích xuất hồ sơ (POST /api/v1/extract-cv?include=kg) | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:24` |
| N10 | action | Trích xuất JSON bằng LLM và làm giàu qua Knowledge Graph | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:100` |
| N11 | decision | AI phản hồi dữ liệu trích xuất hợp lệ? | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:26` |
| N12 | action | Lưu tệp vào đĩa và ghi dữ liệu trích xuất vào CSDL | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:69` |
| N13 | action | Chuyển sang Bước 2 và hiển thị các trường hồ sơ | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:130` |
| N14 | action | Kiểm tra và chỉnh sửa nội dung các trường thông tin | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:274` |
| N15 | action | Nhấn nút Xác nhận hồ sơ | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:281` |
| N16 | decision | Đã có tệp CV được tải lên? | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:140` |
| N17 | action | Hiển thị thông báo hãy tải CV trước | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:141` |
| N18 | action | Gửi yêu cầu xác nhận hồ sơ (PUT /api/cvs) | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:146` |
| N19 | action | Kiểm tra quyền ứng viên và các trường cho phép | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:87` |
| N20 | decision | Dữ liệu xác nhận hợp lệ? | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:92` |
| N21 | action | Lưu hồ sơ vào cv_data và đồng bộ sang identity-service | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:104` |
| N22 | action | Chuyển sang Bước 3 và hiển thị giao diện Hồ sơ của bạn | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:149` |
| N23 | merge | Gộp luồng thông báo lỗi | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:133` |
| N24 | action | Hiển thị thông báo lỗi qua toast | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:133` |
| N25 | final | Kết thúc | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:217` |

---

## Nguồn bổ sung và mâu thuẫn

- **Mô hình lưu trữ Entity-Attribute-Value (EAV):** Thay vì tạo các cột cố định trong bảng hồ sơ, `recruitment-service` lưu trữ thông tin CV dưới dạng các cặp `(field, value)` đa dòng trong bảng `cv_data` (`CvData.java:10`). Việc quản lý cấu hình các trường được điều khiển bởi `SettingService` với key `CV_FIELD` (mặc định gồm 9 trường: *Họ tên, Email, Điện thoại, Tóm tắt, Kỹ năng, Kỹ năng suy ra, Học vấn, Kinh nghiệm, Chứng chỉ*).
- **Giao tiếp liên dịch vụ (Service-to-Service):** Khi xác nhận hồ sơ, `CvService.syncProfile` chủ động gọi sang `identity-service` qua `IdentityClient.update` (`IdentityClient.java:13`) thông qua endpoint nội bộ `PATCH /internal/users/{id}`, được bảo vệ bởi secret token `X-Service-Token`. Điều này đảm bảo tính nhất quán dữ liệu người dùng mà không cần vi phạm nguyên tắc Database-per-Service.
- **Giải thuật trích xuất văn bản:** `PdfTextExtractor` (`PdfTextExtractor.java:24`) tự hiện thực giải thuật phát hiện cột và phân chia khối văn bản bằng kỹ thuật Recursive XY-cut dựa trên thư viện Apache PDFBox. Giới hạn `MAX_PAGES = 10` và `MIN_TEXT_CHARS = 50` là các ngưỡng nghiệp vụ cứng được định nghĩa trong mã nguồn nhằm ngăn chặn tấn công DoS và loại trừ các tài liệu quét không đọc được văn bản.
- **Tài liệu và mã nguồn:** Tài liệu `source/recruit_system/docs/Module3_Interview_Flow.md` chỉ đặc tả luồng phỏng vấn AI, không bao gồm module M2. File PDF báo cáo đồ án chưa có trên đĩa. Toàn bộ kịch bản, các bước kiểm tra, mã lỗi và tên phương thức đều được đối soát chính xác 100% từ mã nguồn thực tế của hệ thống microservices tại commit `1c96706`.

---

## Cần xác nhận

- [cần xác nhận] Hệ thống hiện tại từ chối trực tiếp các CV dạng ảnh quét (scanned PDF) thiếu text layer với mã 422 ("PDF has no readable text; OCR is required for scanned CVs"). Có dự định bổ sung OCR worker trong tương lai hay duy trì nguyên tắc chỉ nhận PDF có text layer sẵn?
- [cần xác nhận] Tại giao diện Bước 3 (`step === 3`), hệ thống cung cấp nút "Cập nhật hồ sơ" cho phép ứng viên quay lại Bước 2 để chỉnh sửa thêm; việc này duy trì vòng lặp cập nhật tại client và không tạo phiên bản lịch sử CV mới trong CSDL.
