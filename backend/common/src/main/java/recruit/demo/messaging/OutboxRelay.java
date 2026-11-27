package recruit.demo.messaging;

import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageBuilder;
import org.springframework.amqp.core.MessageDeliveryMode;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.transaction.support.TransactionTemplate;

import java.nio.charset.StandardCharsets;
import java.sql.Timestamp;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.concurrent.TimeUnit;

/** Đọc các sự kiện chưa gửi từ {@code outbox_events} (FOR UPDATE SKIP LOCKED) và đẩy lên RabbitMQ với publisher confirm. */
@Slf4j
public class OutboxRelay {

    private static final int BATCH_SIZE = 50;
    private static final long CONFIRM_TIMEOUT_SEC = 5L;

    private final JdbcTemplate jdbc;
    private final RabbitTemplate rabbitTemplate;
    private final TransactionTemplate tx;

    public OutboxRelay(JdbcTemplate jdbc, RabbitTemplate rabbitTemplate, TransactionTemplate tx) {
        this.jdbc = jdbc;
        this.rabbitTemplate = rabbitTemplate;
        this.tx = tx;
    }

    @Scheduled(fixedDelayString = "${app.outbox.poll-ms:1000}")
    public void relayBatch() {
        tx.executeWithoutResult(status -> {
            List<OutboxEvent> pending = jdbc.query(
                    "SELECT id, event_id, routing_key, payload, attempts FROM outbox_events " +
                            "WHERE published_at IS NULL ORDER BY id ASC LIMIT " + BATCH_SIZE + " FOR UPDATE SKIP LOCKED",
                    (rs, rowNum) -> OutboxEvent.builder()
                            .id(rs.getLong("id"))
                            .eventId(rs.getString("event_id"))
                            .routingKey(rs.getString("routing_key"))
                            .payload(rs.getString("payload"))
                            .attempts(rs.getInt("attempts"))
                            .build());
            for (OutboxEvent event : pending) {
                // Lỗi đầu tiên thường là broker chậm/sập: dừng lượt này để không giữ khoá dòng quá lâu.
                if (!publishOne(event)) break;
            }
        });
    }

    /** @return true nếu RabbitMQ đã nhận và route được message. */
    boolean publishOne(OutboxEvent event) {
        try {
            Message msg = MessageBuilder
                    .withBody(event.getPayload().getBytes(StandardCharsets.UTF_8))
                    .setContentType(MessageProperties.CONTENT_TYPE_JSON)
                    .setMessageId(event.getEventId())
                    .setDeliveryMode(MessageDeliveryMode.PERSISTENT)
                    .build();
            CorrelationData correlation = new CorrelationData(event.getEventId());
            rabbitTemplate.send(NotificationConstants.EXCHANGE, event.getRoutingKey(), msg, correlation);
            CorrelationData.Confirm confirm = correlation.getFuture().get(CONFIRM_TIMEOUT_SEC, TimeUnit.SECONDS);
            if (correlation.getReturned() != null) {
                // mandatory + không có queue nào nhận: broker vẫn ack nhưng message đã bị bỏ -> gửi lại sau.
                recordFailure(event.getId(), "Unroutable: " + correlation.getReturned().getReplyText());
                return false;
            }
            if (confirm != null && confirm.isAck()) {
                jdbc.update("UPDATE outbox_events SET published_at = ?, last_error = NULL WHERE id = ?",
                        Timestamp.from(Instant.now()), event.getId());
                return true;
            }
            recordFailure(event.getId(), confirm != null ? confirm.getReason() : "Broker nack");
            return false;
        } catch (Exception ex) {
            log.warn("Outbox publish failed for eventId={}: {}", event.getEventId(), ex.getClass().getSimpleName());
            recordFailure(event.getId(), ex.getMessage());
            return false;
        }
    }

    private void recordFailure(Long id, String error) {
        String truncated = error == null ? "Unknown error" : (error.length() > 500 ? error.substring(0, 500) : error);
        jdbc.update("UPDATE outbox_events SET attempts = attempts + 1, last_error = ? WHERE id = ?",
                truncated, id);
    }

    @Scheduled(cron = "${app.outbox.cleanup-cron:0 0 3 * * *}")
    public void cleanupOld() {
        Timestamp cutoff = Timestamp.from(Instant.now().minus(7, ChronoUnit.DAYS));
        int deleted = jdbc.update("DELETE FROM outbox_events WHERE published_at IS NOT NULL AND published_at < ?", cutoff);
        if (deleted > 0) {
            log.info("Cleaned up {} published outbox events older than 7 days", deleted);
        }
    }
}
