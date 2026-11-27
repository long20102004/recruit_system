package recruit.demo.messaging;

import org.springframework.jdbc.core.JdbcTemplate;
import tools.jackson.databind.ObjectMapper;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.UUID;

/** Ghi sự kiện vào bảng {@code outbox_events} trong cùng transaction với nghiệp vụ. */
public class OutboxWriter {

    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper;

    public OutboxWriter(JdbcTemplate jdbc, ObjectMapper objectMapper) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
    }

    public String add(String routingKey, NotificationEvent event) {
        if (event == null || event.getRecipientUserIds() == null || event.getRecipientUserIds().isEmpty()) {
            return null;
        }
        if (event.getEventId() == null || event.getEventId().isBlank()) {
            event.setEventId(UUID.randomUUID().toString());
        }
        if (event.getVersion() <= 0) {
            event.setVersion(1);
        }
        if (event.getOccurredAt() == null) {
            event.setOccurredAt(Instant.now());
        }
        String payload = objectMapper.writeValueAsString(event);
        jdbc.update(
                "INSERT INTO outbox_events (event_id, routing_key, payload, created_at, attempts) VALUES (?, ?, ?, ?, 0)",
                event.getEventId(), routingKey, payload, Timestamp.from(event.getOccurredAt()));
        return event.getEventId();
    }
}
