package recruit.demo.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import recruit.demo.config.AuthProperties;
import recruit.demo.dto.AuthDtos.*;
import recruit.demo.enums.Role;
import recruit.demo.entity.User;
import recruit.demo.enums.UserStatus;
import recruit.demo.exception.BusinessException;
import recruit.demo.repository.UserRepository;
import recruit.demo.security.JwtService;
import recruit.demo.service.OneTimeTokenService.Purpose;

import java.time.LocalDateTime;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** specs/003-auth-flow US1–US3. */
class AuthServiceTest {

    private static final BCryptPasswordEncoder ENCODER = new BCryptPasswordEncoder(4);
    private static final String HASH = ENCODER.encode("abc12345");

    private UserRepository repo;
    private JwtService jwt;
    private LoginAttemptService attempts;
    private OneTimeTokenService tokens;
    private AuthMailService mail;
    private UserCacheInvalidator cache;
    private AuthService service;

    @BeforeEach
    void setUp() {
        repo = mock(UserRepository.class);
        jwt = mock(JwtService.class);
        attempts = mock(LoginAttemptService.class);
        tokens = mock(OneTimeTokenService.class);
        mail = mock(AuthMailService.class);
        cache = mock(UserCacheInvalidator.class);
        when(jwt.generateToken(any(), any(), any())).thenReturn("jwt");
        when(attempts.lockedForSeconds(anyString())).thenReturn(Optional.empty());
        when(repo.save(any(User.class))).thenAnswer(i -> i.getArgument(0));
        service = new AuthService(repo, ENCODER, jwt, new AuthProperties(), attempts, tokens, mail, cache);
    }

    private static User user(boolean verified, UserStatus status) {
        return User.builder().id(9).email("a@x.test").fullName("A").passwordHash(HASH).role(Role.CANDIDATE)
                .status(status).emailVerifiedAt(verified ? LocalDateTime.now() : null).build();
    }

    // ── Đăng ký / xác thực ──────────────────────────────

    @Test
    void registerCreatesUnverifiedUserAndSendsLinkWithoutSession() {
        when(repo.save(any(User.class))).thenAnswer(i -> { User u = i.getArgument(0); u.setId(9); return u; });
        when(tokens.issue(eq(Purpose.VERIFY), eq(9), any())).thenReturn("tok");

        RegisterResponse res = service.register(new RegisterRequest("  A@X.test ", "abc12345"));

        assertEquals("a@x.test", res.email());
        verify(repo).save(argThat(u -> u.getEmailVerifiedAt() == null && u.getEmail().equals("a@x.test")));
        verify(mail).sendVerification("a@x.test", "a", "tok");
        verifyNoInteractions(jwt);
    }

    @Test
    void registerRejectsDuplicateEmail() {
        when(repo.existsByEmailIgnoreCase("a@x.test")).thenReturn(true);
        BusinessException ex = assertThrows(BusinessException.class,
                () -> service.register(new RegisterRequest("a@x.test", "abc12345")));
        assertEquals(2002L, ex.getCode());
    }

    @Test
    void verifyEmailMarksVerifiedAndLogsIn() {
        User u = user(false, UserStatus.ACTIVE);
        when(tokens.consume(Purpose.VERIFY, "tok")).thenReturn(Optional.of(9));
        when(repo.findById(9)).thenReturn(Optional.of(u));

        AuthResponse res = service.verifyEmail(new TokenRequest("tok"));

        assertEquals("jwt", res.token());
        assertNotNull(u.getEmailVerifiedAt());
    }

    @Test
    void verifyEmailRejectsUsedOrExpiredLink() {
        when(tokens.consume(Purpose.VERIFY, "tok")).thenReturn(Optional.empty());
        BusinessException ex = assertThrows(BusinessException.class, () -> service.verifyEmail(new TokenRequest("tok")));
        assertEquals(2006L, ex.getCode());
    }

    @Test
    void resendSkipsVerifiedAndUnknownEmailsWithSameMessage() {
        when(repo.findByEmailIgnoreCase("v@x.test")).thenReturn(Optional.of(user(true, UserStatus.ACTIVE)));
        when(repo.findByEmailIgnoreCase("n@x.test")).thenReturn(Optional.empty());

        String m1 = service.resendVerification(new EmailRequest("v@x.test")).message();
        String m2 = service.resendVerification(new EmailRequest("n@x.test")).message();

        assertEquals(m1, m2);
        verifyNoInteractions(mail);
    }

    // ── Đăng nhập ───────────────────────────────────────

    @Test
    void loginSuccessResetsFailures() {
        when(repo.findByEmailIgnoreCase("a@x.test")).thenReturn(Optional.of(user(true, UserStatus.ACTIVE)));
        assertEquals("jwt", service.login(new LoginRequest("A@x.test", "abc12345")).token());
        verify(attempts).reset("a@x.test");
    }

    @Test
    void wrongPasswordAndUnknownEmailLookIdentical() {
        when(repo.findByEmailIgnoreCase("a@x.test")).thenReturn(Optional.of(user(true, UserStatus.ACTIVE)));
        when(repo.findByEmailIgnoreCase("n@x.test")).thenReturn(Optional.empty());

        BusinessException wrong = assertThrows(BusinessException.class,
                () -> service.login(new LoginRequest("a@x.test", "wrong999")));
        BusinessException unknown = assertThrows(BusinessException.class,
                () -> service.login(new LoginRequest("n@x.test", "wrong999")));

        assertEquals(wrong.getCode(), unknown.getCode());
        assertEquals(wrong.getMessage(), unknown.getMessage());
        assertEquals(2001L, wrong.getCode());
        verify(attempts).recordFailure("a@x.test");
        verify(attempts).recordFailure("n@x.test");
    }

    @Test
    void failureThatReachesThresholdReturnsTemporaryLock() {
        when(repo.findByEmailIgnoreCase("a@x.test")).thenReturn(Optional.of(user(true, UserStatus.ACTIVE)));
        when(attempts.recordFailure("a@x.test")).thenReturn(true);
        BusinessException ex = assertThrows(BusinessException.class,
                () -> service.login(new LoginRequest("a@x.test", "wrong999")));
        assertEquals(2004L, ex.getCode());
    }

    @Test
    void temporaryLockRejectsEvenCorrectPasswordWithoutCounting() {
        when(attempts.lockedForSeconds("a@x.test")).thenReturn(Optional.of(600L));
        BusinessException ex = assertThrows(BusinessException.class,
                () -> service.login(new LoginRequest("a@x.test", "abc12345")));
        assertEquals(2004L, ex.getCode());
        verify(attempts, never()).recordFailure(anyString());
        verifyNoInteractions(repo);
    }

    @Test
    void unverifiedEmailIsReportedOnlyWithCorrectPassword() {
        when(repo.findByEmailIgnoreCase("a@x.test")).thenReturn(Optional.of(user(false, UserStatus.ACTIVE)));
        assertEquals(2003L, assertThrows(BusinessException.class,
                () -> service.login(new LoginRequest("a@x.test", "abc12345"))).getCode());
        assertEquals(2001L, assertThrows(BusinessException.class,
                () -> service.login(new LoginRequest("a@x.test", "wrong999"))).getCode());
    }

    @Test
    void bannedAccountIsReportedOnlyWithCorrectPassword() {
        when(repo.findByEmailIgnoreCase("a@x.test")).thenReturn(Optional.of(user(true, UserStatus.BANNED)));
        assertEquals(2005L, assertThrows(BusinessException.class,
                () -> service.login(new LoginRequest("a@x.test", "abc12345"))).getCode());
        assertEquals(2001L, assertThrows(BusinessException.class,
                () -> service.login(new LoginRequest("a@x.test", "wrong999"))).getCode());
    }

    // ── Quên / đặt lại mật khẩu ─────────────────────────

    @Test
    void forgotPasswordSendsOnlyToActiveAccounts() {
        when(repo.findByEmailIgnoreCase("a@x.test")).thenReturn(Optional.of(user(true, UserStatus.ACTIVE)));
        when(repo.findByEmailIgnoreCase("b@x.test")).thenReturn(Optional.of(user(true, UserStatus.BANNED)));
        when(tokens.tryAcquireCooldown(eq(Purpose.RESET), anyString(), any())).thenReturn(true);
        when(tokens.issue(eq(Purpose.RESET), eq(9), any())).thenReturn("tok");

        String m1 = service.forgotPassword(new EmailRequest("a@x.test")).message();
        String m2 = service.forgotPassword(new EmailRequest("b@x.test")).message();
        String m3 = service.forgotPassword(new EmailRequest("nobody@x.test")).message();

        assertEquals(m1, m2);
        assertEquals(m1, m3);
        verify(mail, times(1)).sendPasswordReset(anyString(), anyString(), anyString());
    }

    @Test
    void forgotPasswordRespectsCooldown() {
        when(repo.findByEmailIgnoreCase("a@x.test")).thenReturn(Optional.of(user(true, UserStatus.ACTIVE)));
        when(tokens.tryAcquireCooldown(eq(Purpose.RESET), anyString(), any())).thenReturn(false);
        service.forgotPassword(new EmailRequest("a@x.test"));
        verifyNoInteractions(mail);
        verify(tokens, never()).issue(any(), any(), any());
    }

    @Test
    void resetPasswordChangesHashRevokesSessionsAndClearsLock() {
        User u = user(false, UserStatus.ACTIVE);
        when(tokens.consume(Purpose.RESET, "tok")).thenReturn(Optional.of(9));
        when(repo.findById(9)).thenReturn(Optional.of(u));

        service.resetPassword(new ResetPasswordRequest("tok", "newpass99"));

        assertTrue(ENCODER.matches("newpass99", u.getPasswordHash()));
        assertNotNull(u.getSessionsValidAfter());
        assertNotNull(u.getEmailVerifiedAt());
        verify(attempts).clear("a@x.test");
        verify(cache).evictAfterCommit(9);
    }

    @Test
    void resetPasswordRejectsInvalidLink() {
        when(tokens.consume(Purpose.RESET, "tok")).thenReturn(Optional.empty());
        assertEquals(2006L, assertThrows(BusinessException.class,
                () -> service.resetPassword(new ResetPasswordRequest("tok", "newpass99"))).getCode());
    }
}
