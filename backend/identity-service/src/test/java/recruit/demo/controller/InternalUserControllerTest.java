package recruit.demo.controller;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import recruit.demo.dto.ServiceDtos.NotificationContext;
import recruit.demo.entity.NotificationPreference;
import recruit.demo.entity.User;
import recruit.demo.enums.NotificationType;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.NotificationPreferenceRepository;
import recruit.demo.repository.UserRepository;
import recruit.demo.security.UserSnapshotCache;
import recruit.demo.service.RbacService;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.when;

/** Unit test cho InternalUserController (/internal/users/{id}/notification-context, FR-006). */
@ExtendWith(MockitoExtension.class)
class InternalUserControllerTest {

    @Mock
    private UserRepository users;
    @Mock
    private UserSnapshotCache userCache;
    @Mock
    private RbacService rbac;
    @Mock
    private NotificationPreferenceRepository notificationPreferences;

    private InternalUserController controller;
    private User user;

    @BeforeEach
    void setUp() {
        controller = new InternalUserController(users, userCache, rbac, notificationPreferences);
        user = User.builder()
                .id(70)
                .email("candidate@example.com")
                .fullName("Nguyen Van A")
                .passwordHash("hash")
                .build();
    }

    @Test
    void usesNotificationTypeDefaultsWhenPreferenceNotConfigured() {
        when(users.findById(70)).thenReturn(Optional.of(user));
        when(notificationPreferences.findById(new NotificationPreference.Key(70, NotificationType.CV_PROCESSED)))
                .thenReturn(Optional.empty());
        when(notificationPreferences.findById(new NotificationPreference.Key(70, NotificationType.APPLICATION_STATUS)))
                .thenReturn(Optional.empty());

        NotificationContext cvCtx = controller.notificationContext(70, NotificationType.CV_PROCESSED);
        assertEquals(new NotificationContext(70, "candidate@example.com", "Nguyen Van A", true, false), cvCtx);

        NotificationContext appCtx = controller.notificationContext(70, NotificationType.APPLICATION_STATUS);
        assertEquals(new NotificationContext(70, "candidate@example.com", "Nguyen Van A", true, true), appCtx);
    }

    @Test
    void usesConfiguredPreferenceOverrides() {
        when(users.findById(70)).thenReturn(Optional.of(user));
        when(notificationPreferences.findById(new NotificationPreference.Key(70, NotificationType.APPLICATION_STATUS)))
                .thenReturn(Optional.of(new NotificationPreference(70, NotificationType.APPLICATION_STATUS, false, true)));
        when(notificationPreferences.findById(new NotificationPreference.Key(70, NotificationType.INTERVIEW_INVITE)))
                .thenReturn(Optional.of(new NotificationPreference(70, NotificationType.INTERVIEW_INVITE, true, false)));

        NotificationContext disabledInApp = controller.notificationContext(70, NotificationType.APPLICATION_STATUS);
        assertEquals(new NotificationContext(70, "candidate@example.com", "Nguyen Van A", false, true), disabledInApp);

        NotificationContext disabledEmail = controller.notificationContext(70, NotificationType.INTERVIEW_INVITE);
        assertEquals(new NotificationContext(70, "candidate@example.com", "Nguyen Van A", true, false), disabledEmail);
    }

    @Test
    void throwsNotFoundWhenUserMissing() {
        when(users.findById(999)).thenReturn(Optional.empty());

        ApiException ex = assertThrows(ApiException.class,
                () -> controller.notificationContext(999, NotificationType.APPLICATION_STATUS));
        assertEquals(HttpStatus.NOT_FOUND, ex.getStatus());
    }
}
