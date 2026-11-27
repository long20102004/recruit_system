package recruit.demo.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import recruit.demo.config.NotificationProperties;
import recruit.demo.entity.EmailDeliveryEntity;
import recruit.demo.enums.EmailDeliveryStatus;
import recruit.demo.repository.EmailDeliveryRepository;

import java.time.Instant;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class EmailDeliveryWorker {

    static final int MAX_ATTEMPTS = 5;
    static final int BATCH_SIZE = 50;
    private static final int MAX_ERROR_LENGTH = 1000;

    private final EmailDeliveryRepository emailDeliveryRepository;
    private final JavaMailSender mailSender;
    private final NotificationProperties properties;

    @Scheduled(fixedDelayString = "${app.notification.email-poll-ms:5000}")
    public void processPendingEmails() {
        List<EmailDeliveryEntity> batch = emailDeliveryRepository.findDue(
                EmailDeliveryStatus.PENDING, MAX_ATTEMPTS, Instant.now(), PageRequest.of(0, BATCH_SIZE));
        for (EmailDeliveryEntity delivery : batch) {
            deliverOne(delivery);
        }
    }

    void deliverOne(EmailDeliveryEntity delivery) {
        try {
            SimpleMailMessage msg = new SimpleMailMessage();
            msg.setFrom(properties.getMailFrom());
            msg.setTo(delivery.getRecipientEmail());
            msg.setSubject(delivery.getSubject());
            msg.setText(buildBody(delivery));
            mailSender.send(msg);

            delivery.setStatus(EmailDeliveryStatus.SENT);
            delivery.setSentAt(Instant.now());
            delivery.setLastError(null);
            emailDeliveryRepository.save(delivery);
        } catch (RuntimeException ex) {
            int nextAttempts = delivery.getAttempts() + 1;
            delivery.setAttempts(nextAttempts);
            delivery.setLastError(truncateError(ex.getMessage()));
            if (nextAttempts >= MAX_ATTEMPTS) {
                delivery.setStatus(EmailDeliveryStatus.FAILED);
            } else {
                delivery.setNextAttemptAt(Instant.now().plus(backoff(nextAttempts)));
            }
            emailDeliveryRepository.save(delivery);
            log.warn("Email delivery id={} failed (attempt {}/{}): {}",
                    delivery.getId(), nextAttempts, MAX_ATTEMPTS, ex.getClass().getSimpleName());
        }
    }

    /** 30s, 1m, 2m, 4m: SMTP gián đoạn vài phút vẫn gửi được. */
    static java.time.Duration backoff(int attempts) {
        return java.time.Duration.ofSeconds(30L << Math.max(0, attempts - 1));
    }

    private String buildBody(EmailDeliveryEntity delivery) {
        String greetingName = (delivery.getRecipientName() != null && !delivery.getRecipientName().isBlank())
                ? delivery.getRecipientName().trim()
                : "bạn";
        StringBuilder sb = new StringBuilder();
        sb.append("Chào ").append(greetingName).append(",\n\n");
        sb.append(delivery.getBodyText());
        if (delivery.getLink() != null && !delivery.getLink().isBlank()) {
            sb.append("\n\nXem chi tiết: ").append(resolveLink(delivery.getLink().trim()));
        }
        sb.append("\n\nHireLens");
        return sb.toString();
    }

    private String resolveLink(String link) {
        if (link.startsWith("http://") || link.startsWith("https://")) {
            return link;
        }
        String base = properties.getFrontendUrl().replaceAll("/+$", "");
        String path = link.startsWith("/") ? link : "/" + link;
        return base + path;
    }

    private static String truncateError(String error) {
        if (error == null || error.isBlank()) {
            return "Mail delivery error";
        }
        return error.length() > MAX_ERROR_LENGTH ? error.substring(0, MAX_ERROR_LENGTH) : error;
    }
}
