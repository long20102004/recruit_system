# M2-SEQ-FE — Biểu đồ tuần tự bên Frontend React (module M2: Tải lên và xác nhận CV)

Đối chiếu với `M2-CLS-FE.json` (biểu đồ lớp cùng bên) và kịch bản `M2-ACT` (N00–N25). Mọi message về Frontend đều là operation có thật trong `M2-CLS-FE.json`; 3 message sang server là request HTTP thật của `CvController` (`@GetMapping/@PostMapping/@PutMapping("/api/cvs")`).

## Lifeline

| Key | Lifeline | Lớp trong M2-CLS-FE | Vai trò |
|---|---|---|---|
| user | Người dùng (actor) | — | Ứng viên (role CANDIDATE, route `/candidate/cv`) |
| uploadZone | :UploadZone | UploadZone | Vùng kéo thả/chọn tệp PDF |
| page | :CandidateCvPage | CandidateCvPage | Trang 3 bước (Tải lên → Kiểm tra → Xác nhận) |
| toastContext | :ToastContext | ToastContext | Context hiển thị toast toàn cục |
| cvsApi | :cvsApi | cvsApi | Nhóm hàm gọi CV API (`mine`/`upload`/`confirm`) |
| server | :CvController | (lifeline đại diện ngoài FE — CvController của recruitment-service) | Nhận request `/api/cvs` qua gateway :8080 |

## Kịch bản (đánh số khớp 1-1 với `seq`)

### Luồng tải hồ sơ hiện có khi mở trang

1. Ứng viên mở trang `/candidate/cv`; React render `CandidateCvPage`.
2. Trang gọi `cvsApi.mine()` trong `useEffect` để lấy hồ sơ hiện có.
3. `cvsApi` gửi `GET /api/cvs` (kèm `Authorization: Bearer <token>`) tới `CvController`.
4. `CvController` trả về `CvFormResponse` (`CvFormDto`: fileName, parsingStatus, analyzed, fields).
5. `cvsApi` trả `CvFormDto` về trang.
6. Trang tự gọi `applyForm(form)`: nạp `fields`/`values`/`fileName`; `step = analyzed ? 3 : (fileName ? 2 : 1)`.

### Luồng tải lên (Step 1)

7. Người dùng kéo thả hoặc chọn tệp PDF; `UploadZone.handleFiles(files)` nhận `FileList`.
8. `UploadZone` gọi callback `onFile(file)` → `CandidateCvPage.onUpload(file)`.
9. **[không phải .pdf]** `onUpload` kiểm tra phần mở rộng, từ chối ngay và gọi `toast("Chỉ nhận file PDF")`.
10. **[hợp lệ .pdf]** `onUpload` gọi `cvsApi.upload(file)`.
11. **[hợp lệ .pdf]** `cvsApi` đóng gói `FormData` và gửi `POST /api/cvs` tới `CvController` (bên trong server: kiểm tra quyền CANDIDATE, trích xuất văn bản, gọi cv-extraction-ai, lưu `cv_data` — xem M2-SEQ-BE/M2-SEQ-AI).
12. **[hợp lệ .pdf]** `CvController` trả `CvFormDto` (các trường đã trích xuất).
13. **[hợp lệ .pdf]** `cvsApi` trả `CvFormDto` về trang.
14. **[hợp lệ .pdf]** Trang tự gọi `applyForm(form, 2)` — chuyển Bước 2, hiển thị biểu mẫu chỉnh sửa.
15. **[hợp lệ .pdf]** Trang gọi `toast("Đã tải CV và điền các mục hồ sơ. Hãy kiểm tra trước khi xác nhận.")`.
16. **[lỗi từ server (ApiError)]** Nếu server trả 4xx/5xx (401/403, file rỗng 400, PDF > 10 trang 400, thiếu text layer 422, lỗi AI 502/503…), `api()` ném `ApiError`; `onUpload` bắt lỗi và `toast(e.message)`.

### Luồng kiểm tra và xác nhận (Step 2 → Step 3)

17. Người dùng chỉnh sửa từng trường; `FieldLines.onChange` → `CandidateCvPage.setField(field, lines)` cập nhật state `values`.
18. Người dùng nhấn nút "Xác nhận hồ sơ" → `onConfirm()`.
19. **[chưa tải CV]** Nếu `fileName` rỗng hoặc là "Chưa chọn file": `toast("Hãy tải CV trước")`, dừng luồng.
20. **[đã có fileName]** Trang gọi `cvsApi.confirm(fields)` với danh sách `CvFieldDto` đã hiệu chỉnh.
21. **[đã có fileName]** `cvsApi` gửi `PUT /api/cvs` với body `{ fields }` tới `CvController` (bên trong server: đối chiếu `CV_FIELD`, cập nhật `cv_data`, đồng bộ identity-service — xem M2-SEQ-BE).
22. **[đã có fileName]** `CvController` trả `CvFormDto` (hồ sơ đã xác nhận, `analyzed`).
23. **[đã có fileName]** `cvsApi` trả `CvFormDto` về trang.
24. **[đã có fileName]** Trang tự gọi `applyForm(form, 3)` — chuyển Bước 3, render "Hồ sơ của bạn" với `LineView`.
25. **[đã có fileName]** Trang gọi `toast("Đã xác nhận hồ sơ")`.
26. **[lỗi từ server (ApiError)]** Nếu xác nhận bị từ chối (401/403, thiếu trường 400 "Thiếu dữ liệu hồ sơ", trường không thuộc `CV_FIELD` 400…): `onConfirm` bắt `ApiError` và `toast(e.message)`.

## Bảng truy vết message → file:dòng

| Seq | From → To | Operation | Nguồn truy vết |
|---|---|---|---|
| 1 | user → page | CandidateCvPage | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:94` |
| 2 | page → cvsApi | mine | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:115` |
| 3 | cvsApi → server | GET /api/cvs | `source/recruit_system/frontend/src/api/client.ts:100` |
| 4 | server → cvsApi | return GET /api/cvs | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:19` |
| 5 | cvsApi → page | return mine | `source/recruit_system/frontend/src/api/client.ts:100` |
| 6 | page → page | applyForm (self) | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:117` |
| 7 | user → uploadZone | handleFiles | `source/recruit_system/frontend/src/components/common/UploadZone.tsx:38` |
| 8 | uploadZone → page | onUpload | `source/recruit_system/frontend/src/components/common/UploadZone.tsx:23` |
| 9 | page → toastContext | toast | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:124` |
| 10 | page → cvsApi | upload | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:129` |
| 11 | cvsApi → server | POST /api/cvs | `source/recruit_system/frontend/src/api/client.ts:104` |
| 12 | server → cvsApi | return POST /api/cvs | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:24` |
| 13 | cvsApi → page | return upload | `source/recruit_system/frontend/src/api/client.ts:101` |
| 14 | page → page | applyForm (self) | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:130` |
| 15 | page → toastContext | toast | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:131` |
| 16 | page → toastContext | toast | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:133` |
| 17 | user → page | setField | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:274` |
| 18 | user → page | onConfirm | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:281` |
| 19 | page → toastContext | toast | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:141` |
| 20 | page → cvsApi | confirm | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:146` |
| 21 | cvsApi → server | PUT /api/cvs | `source/recruit_system/frontend/src/api/client.ts:108` |
| 22 | server → cvsApi | return PUT /api/cvs | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/controller/CvController.java:29` |
| 23 | cvsApi → page | return confirm | `source/recruit_system/frontend/src/api/client.ts:106` |
| 24 | page → page | applyForm (self) | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:149` |
| 25 | page → toastContext | toast | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:150` |
| 26 | page → toastContext | toast | `source/recruit_system/frontend/src/pages/candidate/CandidateCvPage.tsx:152` |

Fragment: `F1` (alt) gồm seq 9–16 với 3 nhánh guard `[không phải .pdf]` / `[hợp lệ .pdf]` / `[lỗi từ server (ApiError)]`; `F2` (alt) gồm seq 19–26 với 3 nhánh guard `[chưa tải CV]` / `[đã có fileName]` / `[lỗi từ server (ApiError)]`.

## Điểm lệch so với biểu đồ hoạt động M2-ACT

1. **Tải hồ sơ khi mount (seq 2–6):** source thật gọi `cvsApi.mine()` trong `useEffect` ngay khi mở trang (`CandidateCvPage.tsx:114-120`); M2-ACT không có bước này (ACT bắt đầu tại N01 người dùng chọn tệp). Đã vẽ đầy đủ theo source và ghi chú để reviewer đối chiếu.
2. **Phần backend/AI của ACT (N05–N12, N19–N21) không vẽ chi tiết:** trong biểu đồ FE chúng gộp vào một lifeline đại diện `:CvController` với 3 message HTTP (`GET`/`POST`/`PUT /api/cvs`). Chi tiết bên trong (CvService, CvExtractionModule, AiJsonClient, identity-service) thuộc M2-SEQ-BE/M2-SEQ-AI.
3. **ACT N24 "Hiển thị thông báo lỗi qua toast":** ở FE, việc hiển thị là gọi `ToastContext.toast(msg)`; `ToastContext` tự render `:Toast` (`ToastContext.tsx:30`). Không vẽ lifeline `:Toast` riêng để giữ ≤ 8 lifeline / ≤ 26 message.
4. **ACT N14 (chỉnh sửa trường):** trên source, thao tác đi qua trung gian `FieldLines.update` (`CandidateCvPage.tsx:51`) trước khi tới `setField`; không có lifeline `FieldLines`, message seq 17 vẽ thẳng user → `setField`.
5. **ACT N22 (Bước 3 hiển thị "Hồ sơ của bạn"):** thể hiện qua seq 24 (`applyForm(form, 3)`, step = 3) và seq 25; việc render `LineView` (`CandidateCvPage.tsx:210`) là nội bộ React, không vẽ message riêng.
6. **ACT N23 (merge lỗi):** trong biểu đồ tuần tự, các luồng lỗi không hội về một điểm mà kết thúc bằng message `toast` trong nhánh `[lỗi từ server (ApiError)]` của từng alt (seq 16, seq 26).

## Mâu thuẫn tài liệu – source

- Không phát hiện mâu thuẫn mới trong phạm vi FE. `source/recruit_system/docs/Module3_Interview_Flow.md` chỉ đặc tả luồng phỏng vấn (M4), không có nội dung về module M2; file PDF báo cáo chưa có trên đĩa nên không đối chiếu được. Toàn bộ thứ tự gọi, tên hàm và route lấy từ source frontend + `CvController.java` (microservices, commit `1c96706`).

## Cần xác nhận (open_questions)

- [cần xác nhận] Có nên vẽ thêm lifeline `:ApiClient` (hàm `api()`, `client.ts:32`, tạo `ApiError` khi `!res.ok`) nằm giữa `:cvsApi` và `:CvController` cho đúng từng tầng gọi fetch không? Hiện tại message HTTP vẽ thẳng từ `:cvsApi` sang `:CvController` theo quy ước "một lifeline đại diện server".
- [cần xác nhận] Bước tải hồ sơ khi mount (seq 2–6) chưa có trong M2-ACT — có cần bổ sung vào M2-ACT để hai biểu đồ khớp 1-1 toàn bộ không?
