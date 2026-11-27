package recruit.demo.messaging;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import recruit.demo.enums.NotificationType;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/** Message contract v1 phát lên exchange {@code hirelens.events}. */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NotificationEvent {
    private String eventId;
    @Builder.Default
    private int version = 1;
    private NotificationType type;
    private Instant occurredAt;
    private List<Integer> recipientUserIds;
    private String title;
    private String body;
    private String link;
    private Map<String, Object> data;
}
