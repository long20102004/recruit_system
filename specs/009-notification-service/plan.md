# Plan · 009 Notification service + RabbitMQ

## Kiến trúc

```
recruitment-service                         RabbitMQ                         notification-service (8084)
 nghiệp vụ + outbox_events (1 TX) ──poll──▶ exchange hirelens.events (topic) ──▶ queue notification.events
 OutboxRelay @Scheduled 1s                   DLX hirelens.events.dlx ─────────▶ queue notification.events.dlq
                                                                                   │ consumer
                                       identity-service ◀── GET /internal/users/{id}/notification-context
                                                                                   ├─ notifications (MySQL riêng)
                                                                                   ├─ email (SMTP / Mailpit)
                                                                                   └─ SSE /api/notifications/stream
```

### Outbox (recruitment-service)

- Bảng `outbox_events(id, event_id UUID unique, routing_key, payload JSON, created_at, published_at NULL, attempts, last_error)`.
- `OutboxWriter.add(routingKey, event)` gọi trong method `@Transactional` nghiệp vụ (cùng TX → FR-001).
- `OutboxRelay` `@Scheduled(fixedDelay=1s)`: lấy ≤ 100 dòng `published_at IS NULL` bằng
  `SELECT ... FOR UPDATE SKIP LOCKED` (MySQL 8, an toàn khi nhiều instance), gửi với **publisher confirm**,
  confirm OK thì set `published_at`; lỗi tăng `attempts`, ghi `last_error`, thử lại vòng sau.
- Dọn dòng đã gửi quá 7 ngày bằng job hằng ngày.
- Code outbox để trong `common` (package `recruit.demo.messaging`) để interview-service dùng lại sau; mỗi service tự có migration bảng.

### RabbitMQ topology (khai báo bằng `Declarables` ở notification-service; recruitment chỉ khai báo exchange)

| Thành phần | Giá trị |
|---|---|
| Exchange | `hirelens.events` (topic, durable) |
| Queue | `notification.events` (durable, `x-dead-letter-exchange=hirelens.events.dlx`) |
| Binding | `application.*`, `cv.*`, `company.*`, `job.*` |
| DLQ | `hirelens.events.dlx` (fanout) → `notification.events.dlq` |
| Routing key | `application.status-changed`, `cv.processed`, `company.reviewed`, `job.locked`; đặt sẵn `job.published`, `company.member-invited` |

Consumer: ack thủ công qua Spring AMQP, retry 3 lần (backoff 1s → 4s), hết thì reject → DLQ (FR-004). `prefetch=10`.

### Message contract `NotificationEvent` v1 (class trong `common`, không dùng record)

```json
{
  "eventId": "uuid", "version": 1, "type": "APPLICATION_STATUS", "occurredAt": "2026-11-27T10:00:00Z",
  "recipientUserIds": [70],
  "title": "Đơn ứng tuyển đã được xem xét",
  "body": "Backend Engineer · Lumen Tech",
  "link": "/candidate/applications/12",
  "data": { "applicationId": 12, "status": "REVIEWING" }
}
```

- Service phát sự kiện tự xác định người nhận (đã có dữ liệu): ứng viên = `CandidateProfile.userId`;
  công ty = mọi `RecruiterProfile.userId` của công ty; tin = `Job.createdById`.
- Nội dung (title/body/link) do service phát soạn, notification-service không cần hiểu nghiệp vụ.
- `type` là `NotificationType` → quyết định cài đặt C14 và tab FE.

### notification-service

- Module Maven mới `backend/notification-service` theo khuôn identity/interview: Spring Boot 4, web, security (JWT dùng chung `common`),
  data-jpa + Flyway + MySQL, `spring-boot-starter-amqp`, `spring-boot-starter-mail`.
- Bảng:
  - `notifications(id, user_id, event_id, type, category, title, body, link, data JSON, read_at, created_at)`,
    unique `(event_id, user_id)` → chống trùng (FR-003); index `(user_id, created_at)`, `(user_id, read_at)`.
  - `email_deliveries(id, notification_id, status, attempts, last_error, sent_at)` để thử gửi lại email lỗi (FR-007).
- Xử lý một sự kiện: với mỗi người nhận → gọi identity `notification-context` (Feign, có `SERVICE_TOKEN`) →
  in-app bật thì insert `notifications` (trùng unique thì bỏ qua) → đẩy SSE → email bật thì ghi `email_deliveries`;
  job `@Scheduled` gửi email (lỗi thử lại tối đa 5 lần).
- SSE: `SseEmitter` theo `userId` (Map trong bộ nhớ, timeout 30 phút, heartbeat 25s). Một instance là đủ cho đồ án;
  scale nhiều instance thì fanout qua queue riêng mỗi instance (ghi chú, chưa làm).

### API (`/api/notifications`, cần đăng nhập, mọi vai trò)

| Method | Path | Trả về |
|---|---|---|
| GET | `?category=&unread=&page=&size=` | `BaseResponse<PageResponse<NotificationDto>>`, mới nhất trước |
| GET | `/unread-count` | `BaseResponse<UnreadCountDto{count}>` |
| POST | `/{id}/read` | `BaseResponse<NotificationDto>`; không phải của mình → 404 |
| POST | `/read-all` | `BaseResponse<UnreadCountDto>` |
| GET | `/stream` | `text/event-stream`: `notification` (NotificationDto), `unread` ({count}), `ping` |

`NotificationDto` (class Lombok): `id, type, category, title, body, link, read, createdAt`.
FE tự map `category` → icon/màu như mock hiện tại.

SSE và auth: `EventSource` không gửi header `Authorization` → FE dùng `fetch` + đọc stream (không thêm thư viện),
gửi Bearer token như API khác.

### identity-service

- `GET /internal/users/{id}/notification-context?type=X` → `{userId, email, fullName, inApp, email}` từ
  `notification_preferences` + mặc định `NotificationType` (FR-006). Bảo vệ bằng `SERVICE_TOKEN` như internal hiện có.
- `NotificationType` thêm `COMPANY_STATUS(true,true)`, `JOB_MODERATION(true,true)`.

### Gateway, hạ tầng

- `api-gateway`: route `notification` → `Path=/api/notifications/**`. Gateway là **server-webmvc**: cần kiểm tra
  SSE không bị buffer (T001). Nếu bị, đặt route stream riêng hoặc cho FE dev proxy thẳng tới 8084.
- `docker-compose.yml`: `rabbitmq:4-management` (5672, UI 15672 bind 127.0.0.1), `notification-db` (MySQL, 3310),
  `notification-service` (8084). Biến: `RABBITMQ_HOST/PORT/USER/PASSWORD`, `NOTIFICATION_URL`, mail dùng lại `MAIL_*` (Mailpit).
- recruitment-service thêm `spring-boot-starter-amqp` + cấu hình RabbitMQ.

### Frontend

- `api/client.ts`: `notificationsApi` (list, unreadCount, markRead, markAllRead, stream).
- Hook `useNotificationStream` (fetch stream, tự nối lại với backoff) cập nhật số chưa đọc cho chuông.
- `NotificationsPage` (C13) và `SiteHeader` dùng API thật; thêm chuông vào layout nhà tuyển dụng.
- `respondInvite` (lời mời công ty) giữ mock — ngoài phạm vi.

## Rủi ro

| Rủi ro | Cách xử lý |
|---|---|
| Gateway MVC buffer SSE | Spike T001 trước khi làm FE stream |
| Gửi trùng (at-least-once) | Unique `(event_id, user_id)`; email gắn với `notification_id` |
| identity sập khi consume | Lỗi → retry → DLQ; xem lại bằng RabbitMQ UI, có thể shovel lại |
| Outbox phình | Job dọn dòng đã gửi > 7 ngày |
| Thứ tự sự kiện | Không cần đảm bảo thứ tự giữa các thông báo |

## File ảnh hưởng

- Mới: `backend/notification-service/**`, `common/.../messaging/**` (NotificationEvent, OutboxEvent, OutboxWriter, OutboxRelay).
- recruitment-service: `pom.xml`, `application.yml`, migration `V12__outbox_events.sql`, phát sự kiện ở
  `ApplicationServiceImpl.transitionStatus`, `CvServiceImpl.store`, `CompanyServiceImpl.approve/reject`, `JobServiceImpl.lockJob`.
- identity-service: `InternalUserController`, `NotificationType` (common), service cài đặt.
- api-gateway `application.yml`; `backend/pom.xml` thêm module; `docker-compose.yml`; `.env.microservices.example`.
- Frontend: `api/client.ts`, hook stream, `NotificationsPage.tsx`, `SiteHeader.tsx`, layout nhà tuyển dụng, bỏ phần list/markRead của `notificationsMock`.

## Kiểm chứng

- Unit: OutboxWriter cùng TX (rollback → không có dòng), OutboxRelay (confirm OK/lỗi), consumer chống trùng,
  tôn trọng cài đặt C14, API chỉ trả thông báo của chính mình.
- Tích hợp: Testcontainers RabbitMQ + MySQL nếu Docker có sẵn (luồng: đổi trạng thái đơn → thông báo + email Mailpit); không có thì ghi rõ.
- Thủ công: tắt RabbitMQ, đổi trạng thái đơn, bật lại → thông báo vẫn tới (FR-002); SSE cập nhật chuông qua gateway.
- `mvn test` các module bị ảnh hưởng (JDK 21), FE `npm run lint && npm run build`.
