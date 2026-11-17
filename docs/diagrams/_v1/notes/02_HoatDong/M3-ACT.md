# M3-ACT — Đối sánh, xem chi tiết việc, ứng tuyển

## Kịch bản chính

1. **N00–N01:** Bắt đầu; người dùng mở trang việc phù hợp qua “Xem xếp hạng”.
2. **N02–N03:** Frontend lấy CV và kiểm tra `analyzed`.
3. **N05–N06:** Tải tin đã đăng, thử lấy điểm đã lưu rồi yêu cầu cập nhật điểm. Nếu lấy điểm cũ lỗi thì dùng danh sách rỗng.
4. **N07–N08:** Recruitment kiểm tra vai trò ứng viên và CV đã phân tích; duyệt các tin `PUBLISHED`. Nếu không có tin, đi thẳng N13.
5. **N09–N12:** Với từng tin, tạo dữ liệu CV/JD, gọi `/match/no-llm`; AI chuẩn hóa, trích đặc trưng, tính điểm và tạo giải thích tất định; backend kiểm tra và lưu kết quả. Lặp tuần tự cho đến hết tin, sau đó sắp xếp giảm dần.
6. **N13–N14:** Hiển thị danh sách xếp hạng hoặc tin đang mở; nếu không có tin thì kết thúc.
7. **N15–N18:** Người dùng chọn chi tiết; frontend kiểm tra mã, tải tin theo ID rồi hiển thị thông tin.
8. **N19–N24:** Người dùng trở về trang chủ, chọn tin và ứng tuyển; frontend gửi yêu cầu, backend kiểm tra và lưu đơn `SUBMITTED`, frontend thông báo thành công.
9. **N26:** Kết thúc.

## Ngoại lệ

1. **N03 → N04 → N26:** CV chưa phân tích: hiển thị hướng dẫn tải CV. `myMatches` ở backend trả danh sách rỗng; `refreshMine` trả 400 nếu CV chưa sẵn sàng.
2. **N08 → N27 → N25 → N26:** Yêu cầu bị từ chối do CV/hồ sơ (400), chưa xác thực (401) hoặc sai vai trò (403); giao diện hiển thị lỗi tải theo catch của trang matching. Trường hợp phản hồi lỗi từ refresh có thể đi theo nhánh dự phòng N08/N13 khi đã tải được tin hoặc điểm cũ.
3. **N11 → N13 → N14:** AI lỗi, ngắt hoặc kết quả không hợp lệ: giữ điểm cũ nếu có; nếu không có điểm nhưng có tin thì hiển thị tin và lỗi chấm. Nếu không có cả điểm lẫn tin và refresh lỗi: **N11 → N27 → N25 → N26**. `AiJsonClient` ánh xạ AI HTTP lỗi sang 502 (trừ 413), mất kết nối/ngắt sang 503; dữ liệu điểm không hợp lệ bị 502. Lỗi hồ sơ CV JSON lưu sai có thể trả 422 trước khi gọi AI: N09 đi N13 khi còn điểm/tin, nếu không đi N27.
4. **N17 → N27 → N25 → N26:** Mã không hữu hạn không gọi API; không tìm thấy tin trả 404 hoặc lỗi tải được toast, đồng thời trang hiện trạng thái không tìm thấy.
5. **N22 → N27 → N25 → N26:** Sai vai trò/chưa xác thực (403/401), thiếu hồ sơ hoặc tin không mở (400), không có tin (404), đã ứng tuyển (409); trang chủ hiện toast lỗi. Backend không bắt buộc CV đã phân tích khi ứng tuyển.

Các nút N27/N25 là phần gộp trình bày: lỗi từng trang được xử lý bởi catch/trạng thái tương ứng, không hàm xử lý lỗi chung. Không biểu diễn yêu cầu CV/JD qua identity-service: việc dựng response thực tế có `identityClient.get`, nhưng không cần thiết để mô tả nhánh nghiệp vụ chính; service này vẫn là phụ thuộc ngoài của recruitment.

## Bảng truy vết node → file:dòng

| Node | Nội dung | Nguồn |
|---|---|---|
| N00 | Bắt đầu | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:21` |
| N01 | Mở trang việc phù hợp | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:141` |
| N02 | Kiểm tra CV đã phân tích | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:30` |
| N03 | CV đã phân tích? | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:32` |
| N04 | Hiển thị hướng dẫn tải CV | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:104` |
| N05 | Tải danh sách việc và điểm đã lưu | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:40` |
| N06 | Yêu cầu cập nhật điểm phù hợp | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:49` |
| N07 | Kiểm tra quyền và CV, duyệt tin đã đăng | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/MatchingService.java:48` |
| N08 | Yêu cầu đối sánh hợp lệ? | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/MatchingService.java:49` |
| N09 | Chuẩn bị hồ sơ và yêu cầu công việc | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/MatchingService.java:101` |
| N10 | Tính điểm và tạo giải thích tự động | `source/recruit_system/services/cv-matching-ai/app/main.py:57` |
| N11 | AI trả kết quả hợp lệ? | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/matching/CvMatchingModule.java:17` |
| N12 | Lưu điểm và xếp hạng kết quả | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/MatchingService.java:135` |
| N13 | Gộp kết quả hiển thị | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:115` |
| N14 | Hiển thị việc phù hợp hoặc tin đang mở | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:115` |
| N15 | Chọn xem chi tiết việc | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:139` |
| N16 | Kiểm tra mã và tải chi tiết việc | `source/recruit_system/frontend/src/pages/candidate/CandidateJobDetailPage.tsx:50` |
| N17 | Tải được chi tiết? | `source/recruit_system/frontend/src/pages/candidate/CandidateJobDetailPage.tsx:51` |
| N18 | Hiển thị chi tiết việc | `source/recruit_system/frontend/src/pages/candidate/CandidateJobDetailPage.tsx:82` |
| N19 | Trở về trang chủ và chọn ứng tuyển | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:211` |
| N20 | Gửi yêu cầu ứng tuyển | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:91` |
| N21 | Kiểm tra quyền, tin và đơn trùng | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/ApplicationService.java:26` |
| N22 | Ứng tuyển hợp lệ? | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/ApplicationService.java:27` |
| N23 | Lưu đơn ứng tuyển | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/ApplicationService.java:38` |
| N24 | Hiển thị kết quả ứng tuyển | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:93` |
| N25 | Hiển thị lỗi hoặc trạng thái trống | `source/recruit_system/frontend/src/pages/candidate/CandidateJobDetailPage.tsx:58` |
| N26 | Kết thúc | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:94` |
| N27 | Gộp luồng lỗi | `source/recruit_system/frontend/src/pages/candidate/CandidateMatchingPage.tsx:61` |

## Nguồn bổ sung và mâu thuẫn

- API thật: `source/recruit_system/frontend/src/api/client.ts:70`, `:89`, `:99`, `:113`; controller: `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/MatchingController.java:17`, `JobsController.java:18`, `JobsController.java:34`, `ApplicationsController.java:17` (các đường dẫn Java cùng thư mục controller).
- Quyền: `source/recruit_system/backend/common/src/main/java/recruit/demo/security/SecurityUtils.java:17` và `:22`; lỗi AI: `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/client/AiJsonClient.java:15`; kiểm tra kết quả: `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/matching/CvMatchingModule.java:17`.
- **Khác cách đánh số module:** `source/recruit_system/docs/Module3_Interview_Flow.md:1` gọi Module 3 là luyện phỏng vấn; task/bản phân chia báo cáo gọi M3 là đối sánh và ứng tuyển. Đây là khác phạm vi/định danh, không suy ra luồng phỏng vấn thuộc biểu đồ này.
- **Khoảng trống giao diện so với phạm vi yêu cầu:** `source/recruit_system/frontend/src/pages/candidate/CandidateJobDetailPage.tsx:153` chỉ có nút ôn phỏng vấn; nút ứng tuyển nằm ở `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:211`. Không có thao tác ứng tuyển trực tiếp trên trang chi tiết.
- `source/recruit_system/services/cv-matching-ai/app/explain.py:28` có giải thích LLM, nhưng luồng này gọi `/match/no-llm` (`source/recruit_system/services/cv-matching-ai/app/main.py:90`), không gọi `explain_match`. `source/recruit_system/services/cv-matching-ai/app/scoring.py:7` và `:22` là trọng số/điểm; đồ thị kỹ năng nằm trong `source/recruit_system/services/cv-matching-ai/app/graph.py:73`.
- Báo cáo PDF chưa có trên đĩa nên không thể kiểm tra trực tiếp mâu thuẫn với PDF. `source/recruit_system/docs/schema.dbml` là lược đồ, không đặc tả kịch bản UI này; không suy diễn luồng từ lược đồ.

## Cần xác nhận

- Có dự định bổ sung nút ứng tuyển ngay trang chi tiết hay tiếp tục ứng tuyển ở trang chủ?
