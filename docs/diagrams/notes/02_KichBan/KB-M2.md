# KB-M2 — Kịch bản tải lên và xác nhận CV

**Bước 1.** Xác định tác nhân là ứng viên và các giao diện chính: xem hồ sơ, tải tài liệu, kiểm tra và xác nhận hồ sơ.

**Bước 2.** Xác định các thao tác, kết quả và các nhánh lỗi theo mã nguồn. Ta được bảng kịch bản chuẩn và ngoại lệ sau:

| Mục | Nội dung |
|---|---|
| Scenario | Tải lên và xác nhận CV |
| Actor | Ứng viên |
| Pre-condition | Ứng viên đã đăng nhập bằng tài khoản seed `candidate@hirelens.local` / `demo1234`, có hồ sơ ứng viên; dịch vụ trích xuất AI sẵn sàng. Có sẵn một tệp PDF thực tế, không rỗng, tối đa 10 trang và có ít nhất 50 ký tự văn bản. Tên tệp minh họa `CV_Nguyen_Minh_An.pdf` lấy từ seed; seed không chứng minh tệp vật lý đó tồn tại. |
| Post-condition | Tệp và dữ liệu trích xuất được lưu; các trường được ứng viên xác nhận được cập nhật; họ tên không rỗng và điện thoại được đồng bộ sang identity-service, tóm tắt được lưu vào hồ sơ ứng viên. Giao diện hiện “Hồ sơ của bạn”. |
| Main events | **1.** Ứng viên chọn “Hồ sơ / CV”.<br>**2.** Hệ thống tải hồ sơ và hiển thị “Hồ sơ của bạn” với dữ liệu seed ở Bảng 1; có “Cập nhật hồ sơ” và “Xem việc phù hợp”. Trạng thái này tương ứng cơ sở dữ liệu mới áp dụng seed và migration, chưa thay đổi.<br>**3.** Ứng viên chọn “Cập nhật hồ sơ”.<br>**4.** Hệ thống hiện “Hồ sơ & phân tích CV”, bước 2 “Kiểm tra”, các trường ở Bảng 1; có vùng “Kéo thả CV PDF vào đây”, “Tải file khác” và “Xác nhận hồ sơ”.<br>**5.** Ứng viên chọn hoặc kéo thả một CV PDF hợp lệ vào vùng tải, ví dụ tệp có tên `CV_Nguyen_Minh_An.pdf`.<br>**6.** Hệ thống kiểm tra tệp, trích xuất văn bản và gọi AI, lưu tệp cùng dữ liệu được trích xuất; hiện bước 2, tên tệp, các trường để kiểm tra và thông báo “Đã tải CV và điền các mục hồ sơ. Hãy kiểm tra trước khi xác nhận.” Các trường như Bảng 1, nhưng giá trị lúc này phụ thuộc tệp và kết quả AI, không mặc định là giá trị seed. Có “Tải file khác”, vùng chọn tệp và “Xác nhận hồ sơ”.<br>**7.** Ứng viên rà soát, sửa các trường nếu cần và chọn “Xác nhận hồ sơ”.<br>**8.** Hệ thống lưu các trường hợp lệ, đồng bộ thông tin liên quan, thông báo “Đã xác nhận hồ sơ” và hiện “Hồ sơ của bạn” với giá trị vừa xác nhận, theo cấu trúc Bảng 1. Các lựa chọn: “Cập nhật hồ sơ”, “Xem việc phù hợp”. |
| Exceptions | **1.1.** Chưa đăng nhập hoặc sai vai trò: điều hướng/quyền truy cập phụ thuộc lớp bảo vệ route; API CV kiểm tra vai trò ứng viên. Không khẳng định màn hình đích cụ thể khi chưa xác minh đầy đủ; xem open_questions.<br>**2.1.** Không lấy được hồ sơ: trang bỏ qua lỗi lấy dữ liệu và sau khi tải xong hiện giao diện “Hồ sơ & phân tích CV”, bước 1; vùng tải tệp và “Tải file khác” hiện, “Xác nhận hồ sơ” bị vô hiệu hóa.<br>**5.1.** Tệp không có đuôi `.pdf`: hiện “Chỉ nhận file PDF”; giữ giao diện trước khi chọn tệp (bước 1 hoặc 2). Backend cũng từ chối tên không hợp lệ hoặc tệp rỗng với 400.<br>**5.2.** PDF hỏng hoặc vượt 10 trang: backend trả 400 “Invalid PDF or too many pages”; hiện thông báo lỗi và giữ giao diện tải/kiểm tra trước đó.<br>**5.3.** PDF có dưới 50 ký tự văn bản: backend trả 422 “PDF has no readable text; OCR is required for scanned CVs”; hiện thông báo lỗi và giữ giao diện tải/kiểm tra trước đó.<br>**5.4.** AI báo vượt context: backend trả 413; AI trả HTTP lỗi, kể cả 503 do model chưa nạp, được backend chuyển thành 502; dữ liệu `data` rỗng hoặc không phải object cũng trả 502. Lỗi kết nối, timeout hoặc phân tích phản hồi phát sinh exception được chuyển thành 503. Hiện thông báo lỗi và giữ giao diện tải/kiểm tra trước đó.<br>**5.5.** Thiếu xác thực, sai vai trò hoặc không tìm thấy hồ sơ ứng viên: API có thể trả 401, 403 hoặc 400 “Candidate profile not found”; trang xử lý lỗi theo cơ chế API chung, không tự chuyển bước. Đích cụ thể của 401 xem open_questions.<br>**5.6.** Không lưu được tệp do lỗi I/O: backend trả 500 “Failed to store file”; hiện thông báo lỗi và giữ giao diện tải/kiểm tra trước đó.<br>**7.1.** Nếu không có tên tệp, trình xử lý hiện “Hãy tải CV trước” và giữ bước kiểm tra; nút xác nhận bình thường bị khóa ở bước 1. Backend cũng kiểm tra tên tệp đã lưu và trả 400 nếu thiếu.<br>**7.2.** Dữ liệu yêu cầu thiếu `fields` hoặc có tên trường ngoài `CV_FIELD`: backend trả 400; hiện thông báo lỗi và giữ giao diện bước 2. Các mục null hoặc tên rỗng được bỏ qua, không bị từ chối theo kiểm tra này. |

### Bảng 1. Các trường hồ sơ và dữ liệu seed tham khảo

Đây là dữ liệu ban đầu sau migration V4/V5, **không phải** khẳng định kết quả AI của tệp tải mới. Trường trống hiển thị “Chưa có thông tin.” ở chế độ xem chi tiết.

| Trường | Giá trị seed tham khảo |
|---|---|
| Họ tên | Nguyễn Minh An |
| Email | candidate@hirelens.local |
| Điện thoại | 0901234567 |
| Tóm tắt | Sinh viên năm cuối CNTT, có kinh nghiệm thực tập backend với Java/Spring Boot và MySQL. |
| Kỹ năng | Git, Java, MySQL, Python, REST API, Spring Boot |
| Kỹ năng suy ra | Chưa có dữ liệu seed |
| Học vấn | Cử nhân CNTT — Đại học Công nghệ Thông tin |
| Kinh nghiệm | Thực tập sinh Backend @ Công ty Demo Soft |
| Chứng chỉ | AWS Cloud Practitioner (minh họa) |

Nguồn: `source/recruit_system/backend/recruitment-service/src/main/resources/db/migration/V2__seed.sql:1`, `source/recruit_system/backend/recruitment-service/src/main/resources/db/migration/V2__seed.sql:61`, `source/recruit_system/backend/recruitment-service/src/main/resources/db/migration/V4__cv_data.sql:47`, `source/recruit_system/backend/recruitment-service/src/main/resources/db/migration/V5__implied_skills_field.sql:1`.

**Lưu ý:** `upload()` đặt `parsing_status = COMPLETED` trước khi người dùng xác nhận; nếu tải lại trang sau tải lên, `mine()` có thể khiến giao diện vào thẳng bước 3. Không đồng nhất trạng thái này với bằng chứng xác nhận riêng (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:72`, `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:103`). Giao diện ghi tối đa 5MB nhưng thành phần tải tệp không tự kiểm tra kích thước (`source/recruit_system/frontend/src/components/common/UploadZone.tsx:12`).

### open_questions

- [cần xác nhận] Đích điều hướng cụ thể khi phiên hết hạn hoặc truy cập sai vai trò và API trả 401/403; không suy đoán từ toast của trang CV.

### Bảng truy vết bước → file:dòng

| Bước | Nguồn |
|---|---|
| Điều kiện trước | `source/recruit_system/README.md:38`; `source/recruit_system/backend/identity-service/src/main/resources/db/migration/V2__seed.sql:3`; `source/recruit_system/backend/recruitment-service/src/main/resources/db/migration/V2__seed.sql:1` |
| 1 | `source/recruit_system/frontend/src/components/common/SiteHeader.tsx:48`; `source/recruit_system/frontend/src/App.tsx:64` |
| 2, 2.1 | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:103`; `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:114`; `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:173`; `source/recruit_system/backend/recruitment-service/src/main/resources/db/migration/V4__cv_data.sql:20` |
| 3–4 | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:213`; `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:228`; `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:243` |
| 5, 5.1 | `source/recruit_system/frontend/src/components/common/UploadZone.tsx:21`; `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:122`; `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:53` |
| 5.2–5.3 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:18`; `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/extraction/pdf/PdfTextExtractor.java:27` |
| 5.4 | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:81`; `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/client/AiJsonClient.java:15`; `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:24`; `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:132` |
| 1.1, 5.5 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:215`; `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:132` |
| 5.6, 6 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:63`; `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:22`; `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:127` |
| 7, 7.1, 7.2 | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:139`; `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:261`; `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:85` |
| 8 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:103`; `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:146`; `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:189` |
