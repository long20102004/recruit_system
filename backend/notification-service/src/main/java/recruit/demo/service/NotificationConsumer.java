package recruit.demo.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.AmqpRejectAndDontRequeueException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import recruit.demo.client.IdentityServiceClient;
import recruit.demo.dto.NotificationDto;
import recruit.demo.dto.ServiceDtos.NotificationContext;
import recruit.demo.entity.EmailDeliveryEntity;
import recruit.demo.entity.NotificationEntity;
import recruit.demo.enums.EmailDeliveryStatus;
import recruit.demo.exception.ApiException;
import recruit.demo.messaging.NotificationConstants;
import recruit.demo.messaging.NotificationEvent;
import recruit.demo.repository.EmailDeliveryRepository;
import recruit.demo.repository.NotificationRepository;
import tools.jackson.databind.ObjectMapper;

import java.time.Instant;
import java.util.Objects;

@Slf4j
@Component
@RequiredArgsConstructor
public class NotificationConsumer {

    private final ObjectMapper objectMapper;
    private final IdentityServiceClient identityServiceClient;
    private final NotificationRepository notificationRepository;
    private final EmailDeliveryRepository emailDeliveryRepository;
    private final SseHub sseHub;

    @RabbitListener(queues = NotificationConstants.QUEUE)
    public void onMessage(Message message) {
        NotificationEvent event = parseEvent(message);
        if (event.getRecipientUserIds() == null || event.getRecipientUserIds().isEmpty()) {
            return;
        }

        event.getRecipientUserIds().stream()
                .filter(Objects::nonNull)
                .distinct()
                .forEach(userId -> processRecipient(event, userId));
    }

    private NotificationEvent parseEvent(Message message) {
        if (message == null || message.getBody() == null || message.getBody().length == 0) {
            throw new AmqpRejectAndDontRequeueException("Empty notification message");
        }
        try {
            NotificationEvent event = objectMapper.readValue(message.getBody(), NotificationEvent.class);
            if (event == null
                    || event.getEventId() == null || event.getEventId().isBlank()
                    || event.getType() == null) {
                throw new AmqpRejectAndDontRequeueException("Malformed notification event metadata");
            }
            return event;
        } catch (AmqpRejectAndDontRequeueException ex) {
            throw ex;
        } catch (Exception ex) {
            log.warn("Invalid notification payload rejected to DLQ: {}", ex.getClass().getSimpleName());
            throw new AmqpRejectAndDontRequeueException("Invalid notification event payload", ex);
        }
    }

    private void processRecipient(NotificationEvent event, Integer userId) {
        NotificationContext ctx;
        try {
            ctx = identityServiceClient.getNotificationContext(userId, event.getType());
        } catch (ApiException ex) {
            if (ex.getStatus() == HttpStatus.NOT_FOUND) {
                log.warn("Skipping notification for missing userId={}", userId);
                return;
            }
            throw ex;
        }
        if (ctx == null) {
            return;
        }

        String title = truncate(event.getTitle() != null ? event.getTitle() : "", 255);
        String link = truncate(event.getLink(), 500);
        Long savedNotificationId = null;

        if (ctx.isInApp() && !notificationRepository.existsByEventIdAndUserId(event.getEventId(), userId)) {
            NotificationEntity entity = NotificationEntity.builder()
                    .userId(userId)
                    .eventId(event.getEventId())
                    .type(event.getType())
                    .category(event.getType().category())
                    .title(title)
                    .body(event.getBody())
                    .link(link)
                    .data(event.getData())
                    .createdAt(Instant.now())
                    .build();
            try {
                NotificationEntity saved = notificationRepository.save(entity);
                savedNotificationId = saved.getId();
                long unreadCount = notificationRepository.countByUserIdAndReadAtIsNull(userId);
                sseHub.pushNotification(userId, NotificationDto.from(saved), unreadCount);
            } catch (DataIntegrityViolationException ex) {
                log.debug("Duplicate notification ignored for eventId={}, userId={}", event.getEventId(), userId);
            }
        }

        if (ctx.isEmailEnabled()
                && ctx.getEmail() != null && !ctx.getEmail().isBlank()
                && !emailDeliveryRepository.existsByEventIdAndUserId(event.getEventId(), userId)) {
            String bodyText = (event.getBody() != null && !event.getBody().isBlank()) ? event.getBody() : title;
            EmailDeliveryEntity delivery = EmailDeliveryEntity.builder()
                    .notificationId(savedNotificationId)
                    .eventId(event.getEventId())
                    .userId(userId)
                    .recipientEmail(ctx.getEmail())
                    .recipientName(ctx.getFullName())
                    .subject(title)
                    .bodyText(bodyText)
                    .link(link)
                    .status(EmailDeliveryStatus.PENDING)
                    .attempts(0)
                    .createdAt(Instant.now())
                    .build();
            try {
                emailDeliveryRepository.save(delivery);
            } catch (DataIntegrityViolationException ex) {
                log.debug("Duplicate email delivery ignored for eventId={}, userId={}", event.getEventId(), userId);
            }
        }
    }

    private static String truncate(String value, int maxLen) {
        if (value == null || value.length() <= maxLen) {
            return value;
        }
        return value.substring(0, maxLen);
    }
}
