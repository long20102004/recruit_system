package recruit.demo.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.amqp.AmqpRejectAndDontRequeueException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import recruit.demo.client.IdentityServiceClient;
import recruit.demo.dto.NotificationDto;
import recruit.demo.dto.ServiceDtos.NotificationContext;
import recruit.demo.entity.EmailDeliveryEntity;
import recruit.demo.entity.NotificationEntity;
import recruit.demo.enums.EmailDeliveryStatus;
import recruit.demo.enums.NotificationType;
import recruit.demo.exception.ApiException;
import recruit.demo.messaging.NotificationEvent;
import recruit.demo.repository.EmailDeliveryRepository;
import recruit.demo.repository.NotificationRepository;
import tools.jackson.databind.ObjectMapper;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class NotificationConsumerTest {

    @Mock
    private IdentityServiceClient identityServiceClient;
    @Mock
    private NotificationRepository notificationRepository;
    @Mock
    private EmailDeliveryRepository emailDeliveryRepository;
    @Mock
    private SseHub sseHub;

    private ObjectMapper objectMapper;
    private NotificationConsumer consumer;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        consumer = new NotificationConsumer(
                objectMapper,
                identityServiceClient,
                notificationRepository,
                emailDeliveryRepository,
                sseHub
        );
    }

    @Test
    void onMessage_createsNotificationPushesSseAndQueuesEmail() {
        NotificationEvent event = NotificationEvent.builder()
                .eventId("evt-100")
                .version(1)
                .type(NotificationType.APPLICATION_STATUS)
                .occurredAt(Instant.parse("2026-11-27T10:00:00Z"))
                .recipientUserIds(List.of(70))
                .title("Đơn ứng tuyển đã được xem xét")
                .body("Backend Engineer · Lumen Tech")
                .link("/candidate/applications/12")
                .data(Map.of("applicationId", 12))
                .build();

        when(identityServiceClient.getNotificationContext(70, NotificationType.APPLICATION_STATUS))
                .thenReturn(new NotificationContext(70, "uv@example.com", "Nguyen Van A", true, true));
        when(notificationRepository.existsByEventIdAndUserId("evt-100", 70)).thenReturn(false);
        when(notificationRepository.save(any(NotificationEntity.class))).thenAnswer(inv -> {
            NotificationEntity entity = inv.getArgument(0);
            entity.setId(55L);
            return entity;
        });
        when(notificationRepository.countByUserIdAndReadAtIsNull(70)).thenReturn(3L);
        when(emailDeliveryRepository.existsByEventIdAndUserId("evt-100", 70)).thenReturn(false);

        consumer.onMessage(toMessage(event));

        ArgumentCaptor<NotificationEntity> notifCap = ArgumentCaptor.forClass(NotificationEntity.class);
        verify(notificationRepository).save(notifCap.capture());
        NotificationEntity savedNotif = notifCap.getValue();
        assertEquals(70, savedNotif.getUserId());
        assertEquals("evt-100", savedNotif.getEventId());
        assertEquals(NotificationType.APPLICATION_STATUS, savedNotif.getType());
        assertEquals("application", savedNotif.getCategory());
        assertEquals("Đơn ứng tuyển đã được xem xét", savedNotif.getTitle());

        verify(sseHub).pushNotification(eq(70), argThat((NotificationDto dto) ->
                dto.getId().equals(55L) && !dto.isRead() && "application".equals(dto.getCategory())), eq(3L));

        ArgumentCaptor<EmailDeliveryEntity> emailCap = ArgumentCaptor.forClass(EmailDeliveryEntity.class);
        verify(emailDeliveryRepository).save(emailCap.capture());
        EmailDeliveryEntity savedEmail = emailCap.getValue();
        assertEquals(55L, savedEmail.getNotificationId());
        assertEquals("evt-100", savedEmail.getEventId());
        assertEquals("uv@example.com", savedEmail.getRecipientEmail());
        assertEquals(EmailDeliveryStatus.PENDING, savedEmail.getStatus());
        assertEquals(0, savedEmail.getAttempts());
    }

    @Test
    void onMessage_duplicateEventUser_doesNotInsertSecondTime() {
        NotificationEvent event = NotificationEvent.builder()
                .eventId("evt-dup")
                .type(NotificationType.INTERVIEW_INVITE)
                .recipientUserIds(List.of(70))
                .title("Mời phỏng vấn")
                .body("Lịch phỏng vấn")
                .build();

        when(identityServiceClient.getNotificationContext(70, NotificationType.INTERVIEW_INVITE))
                .thenReturn(new NotificationContext(70, "uv@example.com", "Nguyen Van A", true, true));
        when(notificationRepository.existsByEventIdAndUserId("evt-dup", 70)).thenReturn(true);
        when(emailDeliveryRepository.existsByEventIdAndUserId("evt-dup", 70)).thenReturn(true);

        consumer.onMessage(toMessage(event));

        verify(notificationRepository, never()).save(any());
        verify(emailDeliveryRepository, never()).save(any());
        verifyNoInteractions(sseHub);
    }

    @Test
    void onMessage_concurrentDuplicateConstraintViolation_isIgnoredGracefully() {
        NotificationEvent event = NotificationEvent.builder()
                .eventId("evt-race")
                .type(NotificationType.CV_PROCESSED)
                .recipientUserIds(List.of(70))
                .title("CV đã xử lý")
                .build();

        when(identityServiceClient.getNotificationContext(70, NotificationType.CV_PROCESSED))
                .thenReturn(new NotificationContext(70, "uv@example.com", "Nguyen Van A", true, false));
        when(notificationRepository.existsByEventIdAndUserId("evt-race", 70)).thenReturn(false);
        when(notificationRepository.save(any())).thenThrow(new DataIntegrityViolationException("Duplicate"));

        assertDoesNotThrow(() -> consumer.onMessage(toMessage(event)));
        verifyNoInteractions(sseHub);
        verify(emailDeliveryRepository, never()).save(any());
    }

    @Test
    void onMessage_respectsC14_inAppDisabledEmailEnabled() {
        NotificationEvent event = NotificationEvent.builder()
                .eventId("evt-c14-1")
                .type(NotificationType.JOB_ALERT)
                .recipientUserIds(List.of(80))
                .title("Việc làm mới")
                .body("Java Developer")
                .link("/jobs/9")
                .build();

        when(identityServiceClient.getNotificationContext(80, NotificationType.JOB_ALERT))
                .thenReturn(new NotificationContext(80, "user80@example.com", "User 80", false, true));
        when(emailDeliveryRepository.existsByEventIdAndUserId("evt-c14-1", 80)).thenReturn(false);

        consumer.onMessage(toMessage(event));

        verify(notificationRepository, never()).save(any());
        verifyNoInteractions(sseHub);

        ArgumentCaptor<EmailDeliveryEntity> emailCap = ArgumentCaptor.forClass(EmailDeliveryEntity.class);
        verify(emailDeliveryRepository).save(emailCap.capture());
        assertNull(emailCap.getValue().getNotificationId());
        assertEquals("user80@example.com", emailCap.getValue().getRecipientEmail());
    }

    @Test
    void onMessage_respectsC14_inAppEnabledEmailDisabled() {
        NotificationEvent event = NotificationEvent.builder()
                .eventId("evt-c14-2")
                .type(NotificationType.CV_PROCESSED)
                .recipientUserIds(List.of(81))
                .title("CV đã xử lý")
                .body("Hoàn tất trích xuất")
                .build();

        when(identityServiceClient.getNotificationContext(81, NotificationType.CV_PROCESSED))
                .thenReturn(new NotificationContext(81, "user81@example.com", "User 81", true, false));
        when(notificationRepository.existsByEventIdAndUserId("evt-c14-2", 81)).thenReturn(false);
        when(notificationRepository.save(any(NotificationEntity.class))).thenAnswer(inv -> {
            NotificationEntity e = inv.getArgument(0);
            e.setId(99L);
            return e;
        });
        when(notificationRepository.countByUserIdAndReadAtIsNull(81)).thenReturn(1L);

        consumer.onMessage(toMessage(event));

        verify(notificationRepository).save(any(NotificationEntity.class));
        verify(sseHub).pushNotification(eq(81), any(NotificationDto.class), eq(1L));
        verify(emailDeliveryRepository, never()).save(any());
    }

    @Test
    void onMessage_corruptJson_throwsAmqpRejectAndDontRequeue() {
        Message bad = new Message("not-json".getBytes(StandardCharsets.UTF_8), new MessageProperties());
        assertThrows(AmqpRejectAndDontRequeueException.class, () -> consumer.onMessage(bad));
    }

    @Test
    void onMessage_identityUnavailable_rethrowsForRetryAndDlq() {
        NotificationEvent event = NotificationEvent.builder()
                .eventId("evt-err")
                .type(NotificationType.COMPANY_STATUS)
                .recipientUserIds(List.of(90))
                .title("Công ty đã duyệt")
                .build();

        when(identityServiceClient.getNotificationContext(90, NotificationType.COMPANY_STATUS))
                .thenThrow(new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Identity down"));

        assertThrows(ApiException.class, () -> consumer.onMessage(toMessage(event)));
    }

    private Message toMessage(NotificationEvent event) {
        byte[] bytes = objectMapper.writeValueAsString(event).getBytes(StandardCharsets.UTF_8);
        return new Message(bytes, new MessageProperties());
    }
}
