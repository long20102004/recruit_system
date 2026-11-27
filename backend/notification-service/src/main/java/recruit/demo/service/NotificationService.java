package recruit.demo.service;

import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.dto.NotificationDto;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.Paging;
import recruit.demo.dto.UnreadCountDto;
import recruit.demo.entity.NotificationEntity;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.NotificationRepository;

import java.time.Instant;

@Service
@RequiredArgsConstructor
public class NotificationService {

    private final NotificationRepository notificationRepository;
    private final SseHub sseHub;

    @Transactional(readOnly = true)
    public PageResponse<NotificationDto> listNotifications(
            Integer userId, String category, Boolean unread, int page, int size) {
        String normalizedCategory = (category == null || category.isBlank()) ? null : category.trim();
        boolean unreadOnly = Boolean.TRUE.equals(unread);
        Pageable pageable = Paging.of(page, size);
        Page<NotificationEntity> result = notificationRepository.findUserNotifications(
                userId, normalizedCategory, unreadOnly, pageable);
        return PageResponse.toPageResponse(result, NotificationDto::from);
    }

    @Transactional(readOnly = true)
    public UnreadCountDto unreadCount(Integer userId) {
        return new UnreadCountDto(notificationRepository.countByUserIdAndReadAtIsNull(userId));
    }

    @Transactional
    public NotificationDto markRead(Integer userId, Long id) {
        NotificationEntity entity = notificationRepository.findByIdAndUserId(id, userId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Không tìm thấy thông báo"));
        if (entity.getReadAt() == null) {
            entity.setReadAt(Instant.now());
            entity = notificationRepository.save(entity);
            sseHub.pushUnread(userId, notificationRepository.countByUserIdAndReadAtIsNull(userId));
        }
        return NotificationDto.from(entity);
    }

    @Transactional
    public UnreadCountDto markAllRead(Integer userId) {
        notificationRepository.markAllRead(userId, Instant.now());
        sseHub.pushUnread(userId, 0);
        return new UnreadCountDto(0);
    }
}
