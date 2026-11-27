# 009 · Notification service + RabbitMQ (màn C13, chuông, C14)

Nguồn: `docs/MISSING_FEATURES.md` mục 5 "Module thông báo". Hiện C13 và chuông dùng `notificationsMock`;
C14 lưu `notification_preferences` (identity-service) nhưng chưa có tác dụng.

## Quyết định đã chốt (2026-11-27)

| Câu hỏi | Chọn |
|---|---|
| Vị trí | **notification-service mới** (cổng 8084, MySQL riêng), consume RabbitMQ |
| Sự kiện đợt này | Các sự kiện **đã có nguồn**; job alert, mời vào công ty chỉ đặt sẵn routing key |
| Realtime | **SSE** đẩy thông báo mới + số chưa đọc |
| Độ tin cậy | **Transactional outbox** ở service phát sự kiện, consumer chống trùng theo `eventId` |

Ngoài phạm vi:
- Job alert (F2-07) và lời mời vào công ty (tính năng 10): chưa có nguồn sự kiện. `respondInvite` ở C13 vẫn mock.
- Push mobile, SMS, gom email theo tần suất (digest).
- interview-service chưa phát sự kiện (lời mời phỏng vấn đi từ việc đổi đơn sang `INTERVIEW` ở recruitment-service).

## User stories

- **US1. Nhận thông báo trong app.** Người dùng thấy danh sách thông báo (C13) theo tab Tất cả / Chưa đọc /
  Ứng tuyển / Phỏng vấn / Job alert / Công ty, phân trang "Xem thêm"; đánh dấu đã đọc từng cái hoặc tất cả.
- **US2. Chuông.** Chuông trên menu (ứng viên và nhà tuyển dụng) hiện số chưa đọc, cập nhật ngay khi có thông báo mới (SSE).
- **US3. Email theo cài đặt.** Thông báo được gửi email khi loại đó bật email trong C14; tắt in-app thì không tạo thông báo trong app.
- **US4. Sự kiện nghiệp vụ.**

| Sự kiện | Người nhận | Loại (C14) | Tab |
|---|---|---|---|
| Đơn đổi trạng thái (REVIEWING, HIRED, REJECTED) | ứng viên | `APPLICATION_STATUS` | Ứng tuyển |
| Đơn chuyển sang INTERVIEW (mời phỏng vấn) | ứng viên | `INTERVIEW_INVITE` | Phỏng vấn |
| AI đọc CV xong | ứng viên | `CV_PROCESSED` | (Tất cả) |
| Công ty được duyệt / bị từ chối | nhà tuyển dụng của công ty | `COMPANY_STATUS` (mới) | Công ty |
| Tin bị admin khoá | nhà tuyển dụng tạo tin | `JOB_MODERATION` (mới) | Công ty |

## Yêu cầu

- FR-001 Ghi sự kiện vào bảng outbox **cùng transaction** với thay đổi nghiệp vụ; nghiệp vụ rollback thì không có sự kiện.
- FR-002 RabbitMQ sập thì nghiệp vụ vẫn chạy; sự kiện được gửi khi RabbitMQ lên lại (at-least-once).
- FR-003 Consumer xử lý trùng `eventId` không tạo thông báo/email lần hai.
- FR-004 Lỗi xử lý thử lại có giới hạn rồi chuyển vào dead-letter queue, không chặn hàng đợi.
- FR-005 Người dùng chỉ đọc/sửa thông báo của mình (lọc theo `userId` trong JWT).
- FR-006 Tôn trọng cài đặt C14: không có dòng cài đặt thì dùng mặc định trong `NotificationType`.
- FR-007 Email lỗi không làm mất thông báo trong app; log không chứa nội dung CV hay token.
- FR-008 SSE gửi sự kiện `notification` (bản ghi mới) và `unread` (số chưa đọc); kết nối tự nối lại phía FE.

## Thay đổi contract

- API mới (qua gateway): `/api/notifications/**`.
- Internal mới ở identity-service: `GET /internal/users/{id}/notification-context?type=` (email, tên, cờ in-app/email).
- Message contract `NotificationEvent` (JSON, version 1) trên exchange `hirelens.events` — mô tả trong plan.
- `NotificationType` thêm `COMPANY_STATUS`, `JOB_MODERATION` → C14 hiện thêm 2 dòng (chỉ nhà tuyển dụng cần).
