# M3-SEQ-BE — Đối sánh, xem chi tiết việc, ứng tuyển (Backend)

## Kịch bản theo message

1. Frontend gửi POST /api/matching/mine/refresh đến refreshMine.
2. Controller gọi service; service kiểm tra vai trò, hồ sơ và CV.
3. Với mỗi tin PUBLISHED, gọi runMatching(request); các thao tác chuẩn bị dữ liệu được lược giản.
4. Gọi match(candidate, jd), với candidate nhận giá trị profile.
5. Gọi post(url, body) với URL /match/no-llm và body chứa candidate, jd.
6. Gửi yêu cầu HTTP tới dịch vụ AI.
7. AI trả JSON điểm và các đặc trưng.
8. Client phân tích JSON và trả JsonNode.
9. Sau kiểm tra điểm và danh sách kỹ năng, module trả kết quả hợp lệ.
10. Service lưu MatchingResult rồi trả MatchResponse cho lần lặp hiện tại.
11. Sau khi xử lý hết tin, service sắp giảm dần và trả danh sách.
12. Controller trả danh sách cho frontend.
13. Sau khi xem chi tiết và trở về trang chủ, frontend gửi POST /api/applications/jobs/{jobId}.
14. Controller gọi apply(jobId, request).
15. Nếu hợp lệ, lưu đơn SUBMITTED và trả ApplicationResponse.
16. Controller trả đơn ứng tuyển cho frontend.
17. Nếu đơn đã tồn tại, service phát sinh ApiException 409.
18. Ngoại lệ được ánh xạ thành phản hồi HTTP 409.

## Truy vết message → file:dòng

| Seq | Nguồn |
|---:|---|
| 1 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/MatchingController.java:22` |
| 2 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/MatchingController.java:24` |
| 3 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/MatchingService.java:57` |
| 4 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/MatchingService.java:125` |
| 5 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/matching/CvMatchingModule.java:18` |
| 6 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/client/AiJsonClient.java:17` |
| 7 | `source/recruit_system/services/cv-matching-ai/app/main.py:90` |
| 8 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/client/AiJsonClient.java:23` |
| 9 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/matching/CvMatchingModule.java:31` |
| 10 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/MatchingService.java:153` |
| 11 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/MatchingService.java:59` |
| 12 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/MatchingController.java:24` |
| 13 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/ApplicationsController.java:17` |
| 14 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/ApplicationsController.java:20` |
| 15 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/ApplicationService.java:44` |
| 16 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/ApplicationsController.java:20` |
| 17 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/ApplicationService.java:34` |
| 18 | `source/recruit_system/backend/common/src/main/java/recruit/demo/exception/GlobalExceptionHandler.java:18` |

## Phạm vi và sai khác so với M3-ACT

- Vẽ lát cắt N06–N12 và N20–N24; N02–N05 và N13–N19 diễn ra ở frontend hoặc là các request riêng, không vẽ. Đặc biệt GET chi tiết việc N16–N18 không vẽ vì giới hạn 8 lifeline; không ngụ ý backend bỏ qua xử lý đó. Nguồn: `source/recruit_system/frontend/src/pages/candidate/CandidateJobDetailPage.tsx:50`, `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/JobsController.java:34`.
- Fragment loop chỉ đánh dấu lời gọi số 3 do schema chỉ hỗ trợ một fragment/message; các message 4–10 là thân một lượt lặp, không ngụ ý chỉ gọi AI một lần cho toàn bộ tin. Không có tin thì vòng lặp không chạy.
- Biểu đồ chỉ vẽ ngoại lệ đơn trùng 409; các lỗi CV/AI/chi tiết việc trong M3-ACT không mất đi. Các nhánh alt kết thúc request ứng tuyển; biểu đồ không ngụ ý tiếp tục sau 409.
- Không vẽ các lời gọi repository và IdentityClient khi tạo response (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/MatchingService.java:135`, `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/MatchingService.java:176`, `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/ApplicationService.java:44`, `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/ApplicationService.java:73`); chúng vẫn thực sự xảy ra. Do đó lưu và tạo response được mô tả ở kịch bản, không tạo message giả.
- HTTP vào controller: `operation` dùng tên phương thức của CLS, trường `http` giữ route request; response trả về dùng tên operation tương ứng. `params` là tên tham số khai báo tại phương thức đích; `candidate` nhận biến `profile` tại call site.

## Mâu thuẫn và tài liệu

- `source/recruit_system/docs/Module3_Interview_Flow.md:1` đặt tên Module 3 cho phỏng vấn; M3 theo phân chia task là đối sánh/ứng tuyển. Vẽ theo source và phạm vi task, không trộn hai luồng.
- Trang chi tiết không có nút ứng tuyển; ứng tuyển tại trang chủ (`source/recruit_system/frontend/src/pages/candidate/CandidateJobDetailPage.tsx:153`, `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:211`).
- Báo cáo PDF chưa có trên đĩa nên không thể đối chiếu trực tiếp.

## Cần xác nhận

- [cần xác nhận] Có nên tách biểu đồ để bổ sung request GET /api/jobs/{id}, JobsController.get và JobService.getById mà vẫn giữ giới hạn 8 lifeline?
- [cần xác nhận] M3-CLS-BE thiếu IdentityClient.get và các operation JpaRepository kế thừa như save/findById cần thể hiện đầy đủ luồng lưu và tạo response; có bổ sung vào biểu đồ lớp hay tiếp tục lược giản?
- [cần xác nhận] Có dự định bổ sung nút ứng tuyển tại trang chi tiết việc hay giữ thao tác ứng tuyển tại trang chủ?
