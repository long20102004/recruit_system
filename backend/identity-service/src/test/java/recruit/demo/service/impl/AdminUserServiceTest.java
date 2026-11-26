package recruit.demo.service.impl;

import recruit.demo.service.*;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import recruit.demo.enums.Role;
import recruit.demo.entity.User;
import recruit.demo.enums.UserStatus;
import recruit.demo.exception.BusinessException;
import recruit.demo.repository.UserRepository;
import recruit.demo.security.UserPrincipal;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/** specs/003-auth-flow US4. */
class AdminUserServiceTest {

    private UserRepository repo;
    private UserCacheInvalidator cache;
    private AdminUserService service;

    @BeforeEach
    void setUp() {
        repo = mock(UserRepository.class);
        cache = mock(UserCacheInvalidator.class);
        when(repo.save(any(User.class))).thenAnswer(i -> i.getArgument(0));
        service = new AdminUserServiceImpl(repo, cache);
        loginAs(1, Role.ADMIN);
    }

    @AfterEach
    void clear() {
        SecurityContextHolder.clearContext();
    }

    private static void loginAs(int id, Role role) {
        var p = new UserPrincipal(id, "u" + id + "@x.test", "", "U", role, UserStatus.ACTIVE);
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(p, null, p.getAuthorities()));
    }

    private void stubUser(int id, Role role, UserStatus status) {
        when(repo.findById(id)).thenReturn(Optional.of(
                User.builder().id(id).email("t@x.test").fullName("T").passwordHash("h").role(role).status(status).build()));
    }

    @Test
    void lockBansRevokesSessionsAndEvictsCache() {
        stubUser(5, Role.CANDIDATE, UserStatus.ACTIVE);
        var dto = service.lock(5, "  spam  ");
        assertEquals(UserStatus.BANNED, dto.getStatus());
        assertEquals("spam", dto.getLockedReason());
        assertNotNull(dto.getLockedAt());
        verify(repo).save(argThat(u -> u.getSessionsValidAfter() != null));
        verify(cache).evictAfterCommit(5);
    }

    @Test
    void cannotLockSelfOrAdmin() {
        stubUser(1, Role.ADMIN, UserStatus.ACTIVE);
        stubUser(2, Role.ADMIN, UserStatus.ACTIVE);
        assertEquals(2007L, assertThrows(BusinessException.class, () -> service.lock(1, "x")).getCode());
        assertEquals(2007L, assertThrows(BusinessException.class, () -> service.lock(2, "x")).getCode());
        verify(repo, never()).save(any());
    }

    @Test
    void unlockRestoresActiveAndKeepsRevocationMark() {
        when(repo.findById(5)).thenReturn(Optional.of(User.builder().id(5).email("t@x.test").fullName("T")
                .passwordHash("h").role(Role.CANDIDATE).status(UserStatus.BANNED).lockedReason("spam")
                .sessionsValidAfter(java.time.LocalDateTime.now()).build()));
        var dto = service.unlock(5);
        assertEquals(UserStatus.ACTIVE, dto.getStatus());
        assertNull(dto.getLockedReason());
        verify(repo).save(argThat(u -> u.getSessionsValidAfter() != null));
        verify(cache).evictAfterCommit(5);
    }
}
