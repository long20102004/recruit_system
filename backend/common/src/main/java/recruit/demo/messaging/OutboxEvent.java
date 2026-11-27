package recruit.demo.messaging;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/** Bản ghi bảng {@code outbox_events} (POJO thuần để tránh yêu cầu bảng ở các service không dùng outbox). */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OutboxEvent {
    private Long id;
    private String eventId;
    private String routingKey;
    private String payload;
    private Instant createdAt;
    private Instant publishedAt;
    private int attempts;
    private String lastError;
}
