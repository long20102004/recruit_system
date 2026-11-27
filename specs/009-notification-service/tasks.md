# Tasks · 009 Notification service + RabbitMQ

## Phase 0 · Spike
- [x] T001 Kiểm tra SSE đi qua `api-gateway` (server-webmvc) không bị buffer; chốt cách route `/api/notifications/stream`

## Phase 1 · Hạ tầng + contract
- [x] T002 `docker-compose.yml`: `rabbitmq:4-management`, `notification-db`, `notification-service`; `.env.microservices.example`
- [x] T003 `common`: `NotificationEvent` (class), `NotificationType` thêm `COMPANY_STATUS`, `JOB_MODERATION`; hằng số exchange/routing key
- [x] T004 `common/messaging`: `OutboxEvent` entity, `OutboxWriter`, `OutboxRelay` (SKIP LOCKED, publisher confirm, dọn 7 ngày) + test

## Phase 2 · Producer: recruitment-service
- [x] T005 `pom.xml` amqp, cấu hình RabbitMQ, migration `V12__outbox_events.sql`, bật relay
- [x] T006 Phát sự kiện: `transitionStatus` (APPLICATION_STATUS / INTERVIEW_INVITE), `CvServiceImpl.store` (CV_PROCESSED),
      `CompanyServiceImpl.approve/reject` (COMPANY_STATUS), `JobServiceImpl.lockJob` (JOB_MODERATION) + test (rollback không sinh sự kiện)

## Phase 3 · identity-service
- [x] T007 `GET /internal/users/{id}/notification-context?type=` + Feign client trong `common` + test mặc định/ghi đè C14

## Phase 4 · notification-service
- [x] T008 Khung module (pom, Application, security JWT, Flyway `V1__notifications.sql`, cấu hình), thêm vào `backend/pom.xml`
- [x] T009 Topology (`Declarables`, DLX/DLQ), consumer (retry 3 lần → DLQ), chống trùng theo `(event_id, user_id)`
- [x] T010 Email: `email_deliveries` + job gửi (Mailpit), tôn trọng cờ email
- [x] T011 API `/api/notifications` (list/unread-count/read/read-all) chỉ của người gọi + test
- [x] T012 SSE `/stream`: registry theo user, heartbeat, đẩy `notification` + `unread`
- [x] T013 Gateway route `/api/notifications/**`

## Phase 5 · Frontend [P] (sau T011, theo contract trong plan)
- [x] T014 `notificationsApi` + hook `useNotificationStream` (fetch stream, tự nối lại)
- [x] T015 `NotificationsPage` (C13) dùng API thật, tab theo `category`, "Xem thêm"; `respondInvite` giữ mock
- [x] T016 Chuông `SiteHeader` + layout nhà tuyển dụng hiện số chưa đọc realtime

## Phase 6 · Kiểm chứng
- [x] T017 `mvn test` (common, recruitment, identity, notification; JDK 21), FE lint + build
- [ ] T018 Thử thật bằng docker compose: đổi trạng thái đơn → thông báo + email Mailpit + chuông cập nhật;
      tắt RabbitMQ giữa chừng → bật lại vẫn nhận (FR-002); xem DLQ khi identity sập
