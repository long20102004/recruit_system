package recruit.demo.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Pageable;
import org.springframework.mail.MailSendException;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import recruit.demo.config.NotificationProperties;
import recruit.demo.entity.EmailDeliveryEntity;
import recruit.demo.enums.EmailDeliveryStatus;
import recruit.demo.repository.EmailDeliveryRepository;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class EmailDeliveryWorkerTest {

    @Mock
    private EmailDeliveryRepository emailDeliveryRepository;
    @Mock
    private JavaMailSender mailSender;

    private NotificationProperties properties;
    private EmailDeliveryWorker worker;

    @BeforeEach
    void setUp() {
        properties = new NotificationProperties();
        properties.setMailFrom("HireLens <no-reply@hirelens.local>");
        properties.setFrontendUrl("http://localhost:5173");
        worker = new EmailDeliveryWorker(emailDeliveryRepository, mailSender, properties);
    }

    @Test
    void processPendingEmails_successMarksSent() {
        EmailDeliveryEntity pending = EmailDeliveryEntity.builder()
                .id(1L)
                .notificationId(10L)
                .eventId("evt-1")
                .userId(70)
                .recipientEmail("uv@example.com")
                .recipientName("Nguyen Van A")
                .subject("Đơn ứng tuyển đã được xem xét")
                .bodyText("Backend Engineer · Lumen Tech")
                .link("/candidate/applications/12")
                .status(EmailDeliveryStatus.PENDING)
                .attempts(0)
                .build();

        when(emailDeliveryRepository.findDue(
                eq(EmailDeliveryStatus.PENDING), eq(5), any(java.time.Instant.class), any(Pageable.class)))
                .thenReturn(List.of(pending));

        worker.processPendingEmails();

        ArgumentCaptor<SimpleMailMessage> mailCap = ArgumentCaptor.forClass(SimpleMailMessage.class);
        verify(mailSender).send(mailCap.capture());
        SimpleMailMessage sentMsg = mailCap.getValue();
        assertEquals("HireLens <no-reply@hirelens.local>", sentMsg.getFrom());
        assertArrayEquals(new String[]{"uv@example.com"}, sentMsg.getTo());
        assertEquals("Đơn ứng tuyển đã được xem xét", sentMsg.getSubject());
        assertNotNull(sentMsg.getText());
        assertTrue(sentMsg.getText().contains("Chào Nguyen Van A,"));
        assertTrue(sentMsg.getText().contains("http://localhost:5173/candidate/applications/12"));

        assertEquals(EmailDeliveryStatus.SENT, pending.getStatus());
        assertNotNull(pending.getSentAt());
        assertNull(pending.getLastError());
        verify(emailDeliveryRepository).save(pending);
    }

    @Test
    void processPendingEmails_failureIncrementsAttemptsAndKeepsPendingBeforeMax() {
        EmailDeliveryEntity pending = EmailDeliveryEntity.builder()
                .id(2L)
                .notificationId(11L)
                .eventId("evt-2")
                .userId(70)
                .recipientEmail("uv@example.com")
                .subject("Thông báo")
                .bodyText("Nội dung")
                .status(EmailDeliveryStatus.PENDING)
                .attempts(2)
                .build();

        when(emailDeliveryRepository.findDue(
                eq(EmailDeliveryStatus.PENDING), eq(5), any(java.time.Instant.class), any(Pageable.class)))
                .thenReturn(List.of(pending));
        doThrow(new MailSendException("SMTP connection refused"))
                .when(mailSender).send(any(SimpleMailMessage.class));

        worker.processPendingEmails();

        assertEquals(3, pending.getAttempts());
        assertEquals(EmailDeliveryStatus.PENDING, pending.getStatus());
        assertTrue(pending.getLastError().contains("SMTP connection refused"));
        assertNull(pending.getSentAt());
        verify(emailDeliveryRepository).save(pending);
    }

    @Test
    void processPendingEmails_fifthFailureMarksFailedWithoutDeletingNotification() {
        EmailDeliveryEntity pending = EmailDeliveryEntity.builder()
                .id(3L)
                .notificationId(12L)
                .eventId("evt-3")
                .userId(70)
                .recipientEmail("uv@example.com")
                .subject("Thông báo")
                .bodyText("Nội dung")
                .status(EmailDeliveryStatus.PENDING)
                .attempts(4)
                .build();

        when(emailDeliveryRepository.findDue(
                eq(EmailDeliveryStatus.PENDING), eq(5), any(java.time.Instant.class), any(Pageable.class)))
                .thenReturn(List.of(pending));
        doThrow(new MailSendException("SMTP timeout"))
                .when(mailSender).send(any(SimpleMailMessage.class));

        worker.processPendingEmails();

        assertEquals(5, pending.getAttempts());
        assertEquals(EmailDeliveryStatus.FAILED, pending.getStatus());
        assertTrue(pending.getLastError().contains("SMTP timeout"));
        verify(emailDeliveryRepository).save(pending);
    }

    @Test
    void failureSchedulesBackoffAndBackoffGrows() {
        EmailDeliveryEntity pending = EmailDeliveryEntity.builder()
                .id(9L).eventId("evt-9").userId(70).recipientEmail("uv@example.com")
                .subject("S").bodyText("B").status(EmailDeliveryStatus.PENDING).attempts(0).build();
        doThrow(new MailSendException("down")).when(mailSender).send(any(SimpleMailMessage.class));

        java.time.Instant before = java.time.Instant.now();
        worker.deliverOne(pending);

        assertEquals(EmailDeliveryStatus.PENDING, pending.getStatus());
        assertTrue(pending.getNextAttemptAt().isAfter(before.plusSeconds(29)));
        assertEquals(java.time.Duration.ofSeconds(30), EmailDeliveryWorker.backoff(1));
        assertEquals(java.time.Duration.ofMinutes(4), EmailDeliveryWorker.backoff(4));
    }
}
