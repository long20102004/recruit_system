package recruit.demo.service.impl;

import org.springframework.beans.factory.ObjectProvider;
import recruit.demo.enums.NotificationType;
import recruit.demo.messaging.NotificationEvent;
import recruit.demo.messaging.OutboxWriter;

import java.util.List;
import java.util.Map;

/** Helper dựng {@link NotificationEvent} và ghi vào {@link OutboxWriter} khi outbox được bật. */
final class NotificationOutbox {

    private NotificationOutbox() {}

    static void publish(ObjectProvider<OutboxWriter> provider,
                        String routingKey,
                        NotificationType type,
                        List<Integer> recipientUserIds,
                        String title,
                        String body,
                        String link,
                        Map<String, Object> data) {
        if (provider == null || recipientUserIds == null || recipientUserIds.isEmpty()) {
            return;
        }
        OutboxWriter writer = provider.getIfAvailable();
        if (writer == null) {
            return;
        }
        writer.add(routingKey, NotificationEvent.builder()
                .type(type)
                .recipientUserIds(recipientUserIds)
                .title(title)
                .body(body)
                .link(link)
                .data(data)
                .build());
    }
}
