# M2-SEQ-BE — Tải lên CV PDF, kiểm tra và xác nhận các trường hồ sơ (Backend)

## Kịch bản theo message

1. Frontend gửi POST /api/cvs với file.
2. Controller gọi service; service kiểm tra ứng viên và file.
3. Service chuyển byte PDF để trích xuất.
4. Module gọi PdfTextExtractor đọc nội dung.
5. PDF hợp lệ trả về nội dung trích xuất. **[PDF hợp lệ, đủ văn bản và AI thành công]**
6. Sau khi kiểm tra độ dài văn bản, module gọi HTTP client.
7. HTTP client gửi văn bản đến dịch vụ AI.
8. AI trả phản hồi cho HTTP client.
9. HTTP client phân tích và trả JSON.
10. Module kiểm tra data và trả hồ sơ trích xuất.
11. Sau khi lưu file và metadata, service ánh xạ các trường.
12. Mapper trả danh sách trường.
13. Sau khi ghi các trường được phép, service tạo biểu mẫu.
14. Service trả biểu mẫu vừa trích xuất.
15. Controller trả biểu mẫu về frontend.
16. PDF không đọc được hoặc quá 10 trang: extractor phát ngoại lệ. **[PDF không hợp lệ hoặc quá 10 trang]**
17. Module chuyển ngoại lệ thành lỗi 400.
18. Ngoại lệ lan từ service đến controller.
19. Lỗi được trả cho frontend; không tiếp tục xác nhận.
20. Sau khi chỉnh sửa, frontend gửi PUT /api/cvs.
21. Controller gọi xác nhận hồ sơ.
22. Với một trường hợp lệ, thay các dòng dữ liệu CV.
23. Đồng bộ trường tương ứng; lời gọi này lặp theo từng trường.
24. Sau vòng lặp và cập nhật trạng thái, dựng biểu mẫu trả về.
25. Service trả biểu mẫu đã xác nhận.
26. Controller trả kết quả xác nhận cho frontend.

Các bước 5–15 và 16–19 là hai nhánh loại trừ; 20–26 là request tiếp theo chỉ sau nhánh thành công và người dùng chỉnh sửa. 22–23 minh họa một lượt trong vòng lặp các trường. Khi lỗi, mũi tên return biểu thị ngoại lệ lan truyền; Spring xử lý thành HTTP response.

## Truy vết message → file:dòng

| Seq | Nguồn |
|---:|---|
| 1 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:22` |
| 2 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:24` |
| 3 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:65` |
| 4 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:20` |
| 5 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/extraction/pdf/PdfTextExtractor.java:188` |
| 6 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:24` |
| 7 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:24` |
| 8 | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:63` |
| 9 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/client/AiJsonClient.java:23` |
| 10 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:25` |
| 11 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:76` |
| 12 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvProfileMapper.java:28` |
| 13 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:79` |
| 14 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:79` |
| 15 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:24` |
| 16 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/extraction/pdf/PdfTextExtractor.java:168` |
| 17 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:21` |
| 18 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:65` |
| 19 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:21` |
| 20 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:27` |
| 21 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:29` |
| 22 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:104` |
| 23 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:105` |
| 24 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:108` |
| 25 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:108` |
| 26 | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:29` |

## Đối chiếu hoạt động và mâu thuẫn

- M2-ACT bao phủ cả frontend, AI và các ngoại lệ khác; biểu đồ này chỉ mô tả backend, rút gọn lưu file, metadata, repository, đồng bộ identity và xử lý frontend. Không vẽ xác nhận sau nhánh lỗi.
- M2-ACT N21 và notes nói đồng bộ identity trong xác nhận như một bước chung; thực tế chỉ khi xử lý trường `Họ tên` có giá trị đầu không rỗng hoặc `Điện thoại`, và gọi riêng từng trường (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:111`). `Tóm tắt` được lưu trong candidate profile.
- M2-ACT notes mô tả lỗi AI HTTP 4xx/5xx thành 502 hoặc rỗng/không phân tích được JSON thành 502; thực tế HTTP 413 được giữ 413, các HTTP lỗi khác thành 502, còn lỗi phân tích JSON rơi vào catch Exception thành 503; `data` không hợp lệ/rỗng mới thành 502 (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/client/AiJsonClient.java:21`, `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/cv/CvExtractionModule.java:25`).
- M2-ACT notes khẳng định backend không lưu dữ liệu hỏng khi lỗi AI: đúng với lỗi trước khi lưu, nhưng không suy ra mọi lỗi sau đó đều xóa file vật lý; file được copy trước khi ghi các trường (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/CvService.java:64`).
- `Module3_Interview_Flow.md` chỉ nói về phỏng vấn, không đặc tả M2; báo cáo PDF chưa có nên không thể đối chiếu.

## Cần xác nhận

- [cần xác nhận] Có bổ sung các phương thức JpaRepository kế thừa save, deleteAll, flush của CvDataRepository và save của CandidateProfileRepository vào M2-CLS-BE để thể hiện rõ ghi dữ liệu trong tuần tự?
- [cần xác nhận] Có cho phép mở rộng giới hạn 8 lifeline để thể hiện IdentityClient, ServiceHttpClient và identity-service cùng đường PATCH /internal/users/{id} trong luồng xác nhận?
