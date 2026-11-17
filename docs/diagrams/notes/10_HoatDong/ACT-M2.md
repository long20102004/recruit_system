# ACT-M2 — Biểu đồ hoạt động chức năng Tải và xác nhận CV

**Bước 1.** Từ biểu đồ lớp chi tiết CLS-M2, xác định một làn giao diện `CandidateCvPage.tsx`; bổ sung các làn `client`, `CvController`, `CvService`, `CandidateProfileRepository`, `CvDataRepository`, `CvExtractionModule`, `PdfTextExtractor`, `AiJsonClient`, `CvProfileMapper`, `IdentityClient` và `cv-extraction-ai`. Module `client` với `api<T>()` và `fetch()` thay cho HTTPClient; controller thật thay cho `requestMapping()`; service và repository thay cho DAO.

**Bước 2.** Xác định các action trong từng làn:

- **CandidateCvPage.tsx:** bắt đầu; gọi `mine()`; hiện giao diện; lấy file từ form; kiểm tra đuôi PDF và thông báo nếu sai; gọi `upload()`; lưu `fields`, `values`, `fileName`, `step` vào state; lấy các trường từ form và lưu `values` vào state; lấy `fileName`, `fields`, `values` từ state; gọi `confirm()`; kết thúc.
- **client:** thực hiện `api<T>()` / `fetch()` và trả kết quả riêng cho ba yêu cầu.
- **CvController:** thực hiện `mine()`, `upload()`, `confirm()` và trả kết quả tương ứng.
- **CvService:** gọi `mine()`, `upload()`, `confirm()`, `syncProfile()`.
- **CandidateProfileRepository:** gọi `findByUserId()` để tìm hồ sơ ứng viên.
- **CvDataRepository:** gọi `findByCandidateIdAndFieldOrderByIdAsc()` để đọc dữ liệu CV.
- **CvExtractionModule:** gọi `extract()` để điều phối trích xuất.
- **PdfTextExtractor:** gọi `extract()` để lấy văn bản PDF.
- **AiJsonClient:** gọi `post()` sang dịch vụ AI.
- **cv-extraction-ai:** thực hiện `extract_cv()` và gọi `generate_cv_result()`.
- **CvProfileMapper:** gọi `fields()` để chuyển kết quả sang các trường hồ sơ.
- **IdentityClient:** gọi `update()` khi đồng bộ họ tên không rỗng hoặc điện thoại.

Ba yêu cầu đi từ trang qua client, controller, service và trả về qua controller, client. Kết quả tải thành công được đưa vào state để kiểm tra; xác nhận thành công hoàn tất, lỗi tải hoặc xác nhận giữ giao diện để thử lại. Nhánh lấy hồ sơ ban đầu thất bại bị bỏ qua, sau đó hiện bước tải lên; không có toast cho lỗi này. Khi có hồ sơ, ứng viên có thể chọn “Cập nhật hồ sơ” để chỉnh sửa. Các kết quả trung gian trong xử lý PDF/AI được gộp vào luồng tiếp theo để bảo đảm tối đa 40 node.

Ta được biểu đồ hoạt động:

**Lưu ý đối chiếu nguồn.** `CvService.upload()` đặt `parsing_status = COMPLETED` ngay sau khi tải và trích xuất, trước khi xác nhận; tải lại có thể mở thẳng bước 3, không chứng minh đã xác nhận (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:72`; `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:103`). Sơ đồ là biểu diễn rút gọn: các lời gọi `requireCandidate()`, `cvFields()`, `replaceLines()` và các vòng lặp, nhánh lỗi trong service không được khai triển đầy đủ; không suy diễn một thứ tự tuần tự bắt buộc giữa các request. Trang thông báo lỗi tải/xác nhận qua toast (`source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:132`, `:151`).

### Câu hỏi mở

- Cần xác nhận đích điều hướng cụ thể khi API trả 401/403 theo KB-M2.
- Với giới hạn 40 node, có cần tách biểu đồ phụ để biểu diễn đầy đủ mọi lời gọi nội bộ và đường trả của AI, repository và service không?
