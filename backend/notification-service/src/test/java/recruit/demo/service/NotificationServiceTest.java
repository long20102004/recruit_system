package recruit.demo.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import recruit.demo.dto.NotificationDto;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.UnreadCountDto;
import recruit.demo.entity.NotificationEntity;
import recruit.demo.enums.NotificationType;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.NotificationRepository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class NotificationServiceTest {

    @Mock
    private NotificationRepository notificationRepository;

    private SseHub sseHub;
    private NotificationService notificationService;

    @BeforeEach
    void setUp() {
        sseHub = org.mockito.Mockito.mock(SseHub.class);
        notificationService = new NotificationService(notificationRepository, sseHub);
    }

    @Test
    void listNotifications_filtersByCallerUserIdCategoryAndUnread() {
        NotificationEntity entity = NotificationEntity.builder()
                .id(10L)
                .userId(70)
                .eventId("evt-1")
                .type(NotificationType.APPLICATION_STATUS)
                .category("application")
                .title("Đơn ứng tuyển")
                .body("Đang xem xét")
                .link("/candidate/applications/1")
                .createdAt(Instant.parse("2026-11-27T10:00:00Z"))
                .build();

        when(notificationRepository.findUserNotifications(
                eq(70), eq("application"), eq(true), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(entity)));

        PageResponse<NotificationDto> page = notificationService.listNotifications(70, " application ", true, 0, 20);

        assertEquals(1, page.getContent().size());
        NotificationDto dto = page.getContent().get(0);
        assertEquals(10L, dto.getId());
        assertEquals("application", dto.getCategory());
        assertFalse(dto.isRead());
        verify(notificationRepository).findUserNotifications(eq(70), eq("application"), eq(true), any(Pageable.class));
    }

    @Test
    void unreadCount_queriesOnlyCallerUserId() {
        when(notificationRepository.countByUserIdAndReadAtIsNull(70)).thenReturn(4L);

        UnreadCountDto dto = notificationService.unreadCount(70);

        assertEquals(4L, dto.getCount());
        verify(notificationRepository).countByUserIdAndReadAtIsNull(70);
    }

    @Test
    void markRead_ownNotification_setsReadAt() {
        NotificationEntity entity = NotificationEntity.builder()
                .id(15L)
                .userId(70)
                .eventId("evt-15")
                .type(NotificationType.INTERVIEW_INVITE)
                .category("interview")
                .title("Mời phỏng vấn")
                .createdAt(Instant.now())
                .build();

        when(notificationRepository.findByIdAndUserId(15L, 70)).thenReturn(Optional.of(entity));
        when(notificationRepository.save(entity)).thenReturn(entity);

        NotificationDto dto = notificationService.markRead(70, 15L);
        verify(sseHub).pushUnread(eq(70), org.mockito.ArgumentMatchers.anyLong());

        assertTrue(dto.isRead());
        assertNotNull(entity.getReadAt());
        verify(notificationRepository).save(entity);
    }

    @Test
    void markRead_otherUsersOrMissingNotification_throwsNotFound() {
        when(notificationRepository.findByIdAndUserId(99L, 70)).thenReturn(Optional.empty());

        ApiException ex = assertThrows(ApiException.class, () -> notificationService.markRead(70, 99L));

        assertEquals(HttpStatus.NOT_FOUND, ex.getStatus());
        verify(notificationRepository, never()).save(any());
    }

    @Test
    void markAllRead_updatesOnlyCallerUserIdAndReturnsZero() {
        when(notificationRepository.markAllRead(eq(70), any(Instant.class))).thenReturn(2);

        UnreadCountDto result = notificationService.markAllRead(70);

        assertEquals(0L, result.getCount());
        verify(notificationRepository).markAllRead(eq(70), any(Instant.class));
        verify(sseHub).pushUnread(70, 0);  // chuông ở các tab khác về 0
    }
}
