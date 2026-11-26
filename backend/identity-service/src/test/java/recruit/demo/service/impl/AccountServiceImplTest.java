package recruit.demo.service.impl;

import recruit.demo.dto.auth.AuthResponse;
import recruit.demo.dto.account.ChangePasswordRequest;
import recruit.demo.dto.account.NotificationPreferenceDto;
import recruit.demo.dto.account.NotificationSettingsDto;
import recruit.demo.dto.account.ProfileResponse;
import recruit.demo.dto.account.UpdateProfileRequest;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import recruit.demo.config.AuthProperties;
import recruit.demo.entity.NotificationPreference;
import recruit.demo.entity.User;
import recruit.demo.enums.Gender;
import recruit.demo.enums.NotificationType;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
import recruit.demo.exception.ApiException;
import recruit.demo.exception.BusinessException;
import recruit.demo.repository.NotificationPreferenceRepository;
import recruit.demo.repository.UserRepository;
import recruit.demo.security.JwtService;
import recruit.demo.security.UserPrincipal;
import recruit.demo.service.LoginAttemptService;
import recruit.demo.service.RbacService;
import recruit.demo.service.UserCacheInvalidator;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** specs/006-account-settings. */
class AccountServiceImplTest {

    private static final BCryptPasswordEncoder ENCODER = new BCryptPasswordEncoder(4);
    private static final String HASH = ENCODER.encode("abc12345");

    private UserRepository users;
    private NotificationPreferenceRepository prefs;
    private LoginAttemptService attempts;
    private UserCacheInvalidator cache;
    private AccountServiceImpl service;
    private User user;

    @BeforeEach
    void setUp() {
        users = mock(UserRepository.class);
        prefs = mock(NotificationPreferenceRepository.class);
        attempts = mock(LoginAttemptService.class);
        cache = mock(UserCacheInvalidator.class);
        JwtService jwt = mock(JwtService.class);
        when(jwt.generateToken(any(), any(), any())).thenReturn("new-jwt");
        RbacService rbac = mock(RbacService.class);
        when(rbac.permissionsOf(any())).thenReturn(List.of("cv:manage-own"));
        when(attempts.lockedForSeconds(anyString())).thenReturn(Optional.empty());
        when(users.save(any(User.class))).thenAnswer(i -> i.getArgument(0));
        service = new AccountServiceImpl(users, prefs, ENCODER, jwt, attempts, new AuthProperties(), cache, rbac);

        user = User.builder().id(9).email("A@x.test").fullName("A").passwordHash(HASH)
                .role(Role.CANDIDATE).status(UserStatus.ACTIVE).build();
        when(users.findById(9)).thenReturn(Optional.of(user));
        var p = new UserPrincipal(9, "a@x.test", "", "A", Role.CANDIDATE, UserStatus.ACTIVE);
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(p, null, p.getAuthorities()));
    }

    @AfterEach
    void clear() {
        SecurityContextHolder.clearContext();
    }

    // ── Hồ sơ ──────────────────────────────────────────

    @Test
    void updateProfileSavesFieldsAndEvictsCache() {
        ProfileResponse res = service.updateProfile(
                new UpdateProfileRequest("  Nguyễn An ", "  ", LocalDate.of(2001, 5, 12), Gender.MALE));

        assertEquals("Nguyễn An", res.getFullName());
        assertNull(res.getPhone());
        assertEquals(LocalDate.of(2001, 5, 12), res.getDateOfBirth());
        assertEquals(Gender.MALE, res.getGender());
        assertEquals("A@x.test", res.getEmail());
        verify(cache).evictAfterCommit(9);
    }

    // ── Đổi mật khẩu ────────────────────────────────────

    @Test
    void changePasswordInvalidatesOtherSessionsAndReturnsNewToken() {
        AuthResponse res = service.changePassword(new ChangePasswordRequest("abc12345", "newpass12"));

        assertEquals("new-jwt", res.getToken());
        assertTrue(ENCODER.matches("newpass12", user.getPasswordHash()));
        assertNotNull(user.getSessionsValidAfter());
        verify(attempts).reset("a@x.test");
        verify(cache).evictAfterCommit(9);
    }

    @Test
    void changePasswordRejectsWrongCurrentAndCountsFailure() {
        BusinessException ex = assertThrows(BusinessException.class,
                () -> service.changePassword(new ChangePasswordRequest("wrong123", "newpass12")));
        assertEquals(2009L, ex.getCode());
        verify(attempts).recordFailure("a@x.test");
        assertEquals(HASH, user.getPasswordHash());

        assertThrows(BusinessException.class,
                () -> service.changePassword(new ChangePasswordRequest(null, "newpass12")));
    }

    @Test
    void changePasswordLocksAfterTooManyFailures() {
        when(attempts.recordFailure("a@x.test")).thenReturn(true);
        BusinessException ex = assertThrows(BusinessException.class,
                () -> service.changePassword(new ChangePasswordRequest("wrong123", "newpass12")));
        assertEquals(2004L, ex.getCode());

        when(attempts.lockedForSeconds("a@x.test")).thenReturn(Optional.of(120L));
        ex = assertThrows(BusinessException.class,
                () -> service.changePassword(new ChangePasswordRequest("abc12345", "newpass12")));
        assertEquals(2004L, ex.getCode());
    }

    @Test
    void changePasswordRejectsSamePassword() {
        assertThrows(ApiException.class,
                () -> service.changePassword(new ChangePasswordRequest("abc12345", "abc12345")));
    }

    @Test
    void googleAccountSetsFirstPasswordWithoutCurrent() {
        user.setPasswordSet(false);

        service.changePassword(new ChangePasswordRequest(null, "newpass12"));

        assertTrue(user.isPasswordSet());
        assertTrue(ENCODER.matches("newpass12", user.getPasswordHash()));
        verifyNoInteractions(attempts);
    }

    // ── Cài đặt thông báo ───────────────────────────────

    @Test
    void notificationSettingsFallBackToDefaults() {
        when(prefs.findByUserId(9)).thenReturn(List.of(
                new NotificationPreference(9, NotificationType.JOB_ALERT, false, false)));

        NotificationSettingsDto res = service.notificationSettings();

        assertEquals(NotificationType.values().length, res.getItems().size());
        var jobAlert = res.getItems().get(NotificationType.JOB_ALERT.ordinal());
        assertEquals(NotificationType.JOB_ALERT, jobAlert.getType());
        assertFalse(jobAlert.isInApp());
        assertFalse(jobAlert.isEmail());
        assertTrue(res.getItems().get(NotificationType.INTERVIEW_INVITE.ordinal()).isEmail());
        assertFalse(res.getItems().get(NotificationType.CV_PROCESSED.ordinal()).isEmail());
    }

    @Test
    @SuppressWarnings("unchecked")
    void updateNotificationSettingsUpsertsRowsForCurrentUser() {
        NotificationPreference existing = new NotificationPreference(9, NotificationType.JOB_ALERT, true, true);
        when(prefs.findByUserId(9)).thenReturn(new ArrayList<>(List.of(existing)));

        service.updateNotificationSettings(new NotificationSettingsDto(List.of(
                new NotificationPreferenceDto(NotificationType.JOB_ALERT, false, true),
                new NotificationPreferenceDto(NotificationType.CV_PROCESSED, true, true))));

        verify(prefs).saveAll(argThat((Collection<NotificationPreference> rows) -> rows.size() == 2
                && rows.stream().allMatch(r -> r.getUserId() == 9)
                && rows.stream().anyMatch(r -> r.getType() == NotificationType.JOB_ALERT && !r.isInApp() && r.isEmail())
                && rows.stream().anyMatch(r -> r.getType() == NotificationType.CV_PROCESSED && r.isEmail())));
    }
}
