# M3-SEQ-FE — Đối sánh, xem chi tiết việc, ứng tuyển (Frontend)

## Phạm vi lát cắt

Biểu đồ vẽ **bước ứng tuyển ở trang chủ** (M3-ACT N19–N24): người dùng bấm nút "Ứng tuyển" trong panel chi tiết việc của `CandidateHomePage`, frontend gửi `POST /api/applications/jobs/{jobId}` và nhận phản hồi.

Lý do chọn lát cắt này: đây là luồng duy nhất trong M3 mà **mọi lời gọi HTTP của frontend đi tới cùng một controller** (`ApplicationsController`), phù hợp ràng buộc "một lifeline đại diện server" và giới hạn 8 lifeline. Luồng đối sánh (N02–N14) gọi ba controller (`CvsController`, `JobsController`, `MatchingController`) và luồng xem chi tiết (N15–N18) gọi `JobsController`; xem mục "Điểm lệch so với M3-ACT" và `open_questions` của spec.

Không vẽ nội bộ backend (service, repository, `IdentityClient`) — chỉ controller nhận request, đúng mức chi tiết của biểu đồ phía client.

## Kịch bản theo message

1. **seq 1** — Người dùng bấm "Ứng tuyển" trong panel chi tiết việc; `CandidateHomePage.apply(selected.id)` được gọi với `jobId`.
2. **seq 2** — Trang gọi `applicationsApi.apply(Number(jobId))`; tham số khai báo của lớp đích là `jobId`.
3. **seq 3** — `applicationsApi.apply` gọi hàm bao `api(path, options)` với `path = "/applications/jobs/{jobId}"`, `options.method = "POST"`.
4. **seq 4** — `api()` gắn header (JSON, `Authorization` nếu có token) và gửi `POST /api/applications/jobs/{jobId}` qua `fetch`; body là `{}` vì trang gọi `apply` chỉ với `jobId` nên `body ?? {}` rỗng.
5. **seq 5** — Nhánh **[đơn được lưu thành công]**: `ApplicationsController.apply(jobId, request)` trả `ApplicationResponse` (HTTP 200, không đặt `@ResponseStatus`).
6. **seq 6** — `api()` đọc JSON và trả `ApplicationDto` cho `applicationsApi`.
7. **seq 7** — `applicationsApi.apply` trả `ApplicationDto` cho trang.
8. **seq 8** — Trang hiện toast "Đã nộp hồ sơ ứng tuyển"; kết quả `ApplicationDto` không được dùng lại.
9. **seq 9** — Nhánh **[chưa đăng nhập, sai vai trò, tin không mở hoặc đã ứng tuyển]**: backend trả lỗi 400 (thiếu hồ sơ ứng viên/tin không mở), 401 (chưa xác thực), 403 (sai vai trò), 404 (không có tin) hoặc 409 (đã ứng tuyển).
10. **seq 10** — `api()` thấy `res.ok === false`, đọc `message` trong `ErrorResponse` rồi ném `ApiError(status, message)`.
11. **seq 11** — Lỗi lan qua `applicationsApi.apply` về `CandidateHomePage.apply` (promise bị reject).
12. **seq 12** — Trang bắt lỗi và hiện toast `e.message` (ví dụ "Already applied to this job").

## Truy vết message → file:dòng

| Seq | Nội dung | Nguồn |
|---:|---|---|
| 1 | Người dùng bấm nút Ứng tuyển | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:212` |
| 2 | `applicationsApi.apply(Number(jobId))` | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:93` |
| 3 | Gọi `api<ApplicationDto>("/applications/jobs/…", { method: "POST" })` | `source/recruit_system/frontend/src/api/client.ts:91` |
| 4 | `fetch(API_BASE + path)` (header ở dòng 40–42, fetch ở dòng 43) | `source/recruit_system/frontend/src/api/client.ts:91` |
| 5 | Controller trả `ApplicationResponse` | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/ApplicationsController.java:20` |
| 6 | `return (await res.json()) as T` | `source/recruit_system/frontend/src/api/client.ts:48` |
| 7 | Promise resolve tại call site | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:93` |
| 8 | `toast("Đã nộp hồ sơ ứng tuyển")` | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:94` |
| 9 | `GlobalExceptionHandler.handleApi` trả đúng status của `ApiException` | `source/recruit_system/backend/common/src/main/java/recruit/demo/exception/GlobalExceptionHandler.java:20` |
| 10 | `throw new ApiError(res.status, await parseError(res))` | `source/recruit_system/frontend/src/api/client.ts:45` |
| 11 | Promise reject tại call site | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:95` |
| 12 | `toast(e instanceof Error ? e.message : "Ứng tuyển thất bại")` | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:96` |

### Nguồn của các mã lỗi ở seq 9

- 403: `AccessDeniedException` → `GlobalExceptionHandler.java:30`.
- 400: thiếu hồ sơ ứng viên (`ApplicationService.java:84`), tin không `PUBLISHED` (`ApplicationService.java:32`).
- 404: không tìm thấy tin (`ApplicationService.java:30`).
- 409: đã có đơn cho tin (`ApplicationService.java:35`).
- 401: do tầng bảo mật JWT của `common` chặn trước controller, không nằm trong `GlobalExceptionHandler`.

## Điểm lệch so với M3-ACT

- **Phạm vi:** chỉ vẽ N19–N24. N01–N18 (mở trang phù hợp, kiểm tra CV, tải việc, đối sánh, xem chi tiết) không nằm trên biểu đồ này; chúng vẫn diễn ra và được mô tả ở `M3-ACT`. Hệ quả là biểu đồ **không** thể hiện việc `CandidateHomePage` đã có `selectedId`/`matchResults` từ trước — thao tác chọn thẻ việc chỉ là `setSelectedId` (state cục bộ), không phải lời gọi API.
- **Lối vào:** M3-ACT N19 mô tả "chọn ứng tuyển"; trong code có hai lối vào: nút trong panel (`CandidateHomePage.tsx:212`) và nút trên thẻ việc (`JobCard.tsx:64-67`, gọi `onApply(job.id)`). Biểu đồ chỉ vẽ lối vào thứ nhất vì `JobCard` không có operation nào trong `M3-CLS-FE.json`.
- **Gộp lỗi:** M3-ACT dùng N27/N25 như nút gộp trình bày; biểu đồ gộp mọi lỗi HTTP vào một nhánh `alt` và kết thúc bằng toast, không có bước hiển thị trạng thái riêng.
- **Không có kiểm tra CV khi ứng tuyển:** đúng như M3-ACT ghi chú; `ApplicationService.apply` không kiểm tra `analyzed` (khác với `refreshMine`).
- **Bước bị lược giản:** `api()` gọi `getToken()` để gắn `Authorization` (`client.ts:40-41`) — không vẽ thành message; `parseError()` (`client.ts:23-30`) cũng không vẽ.

## Nhất quán với biểu đồ lớp

- 5 lifeline object, trong đó 4 lifeline nội bộ đều có trong `M3-CLS-FE.json`: `CandidateHomePage`, `ToastProvider`, `applicationsApi`, `client` (element key `api`); lifeline thứ năm là `ApplicationsController` — bên ngoài, đại diện server.
- Operation dùng lại đúng chữ ký CLS: `CandidateHomePage.apply(jobId: string)`, `applicationsApi.apply(jobId: number, body?)`, `client.api(path, options)`, `ToastProvider.toast(msg)`.
- `applicationsApi.apply` trong CLS có tham số thứ hai `body`; trang gọi với một tham số nên request body là `{}` (`client.ts:93`).

## Mâu thuẫn và nguồn

- **Khác cách đánh số module:** `source/recruit_system/docs/Module3_Interview_Flow.md:1` gọi Module 3 là luyện phỏng vấn; phân chia của dự án gọi M3 là đối sánh/ứng tuyển. Vẽ theo phạm vi task, không trộn luồng phỏng vấn.
- **Trang chi tiết việc không có nút ứng tuyển:** `CandidateJobDetailPage.tsx:153` chỉ có nút "Ôn tập phỏng vấn"; ứng tuyển nằm ở trang chủ (`CandidateHomePage.tsx:211`). Đây là lý do biểu đồ bắt đầu từ `CandidateHomePage`, không phải trang chi tiết.
- **Tài liệu PDF chưa có trên đĩa** nên không đối chiếu trực tiếp được với báo cáo v6.
- `source/recruit_system/docs/schema.dbml` chỉ là lược đồ dữ liệu, không đặc tả luồng UI; không dùng để suy diễn thứ tự gọi.
- Không thấy mâu thuẫn giữa M3-ACT và source ở lát cắt này: các mã lỗi và việc không kiểm tra CV khi ứng tuyển đều khớp `ApplicationService`.

## Cần xác nhận

- Có bổ sung operation `onApply`/`onClick` cho `JobCard` trong `M3-CLS-FE.json` để vẽ được lối vào từ thẻ việc không?
- Có cần thêm biểu đồ riêng cho luồng đối sánh phía frontend (ba controller) không?
- Có cần hiển thị trạng thái đơn sau khi nộp thay vì bỏ qua `ApplicationDto` không?
