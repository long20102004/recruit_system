package recruit.demo.service.impl;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import recruit.demo.entity.AppPermission;
import recruit.demo.entity.AppRole;
import recruit.demo.enums.Role;
import recruit.demo.exception.BusinessException;
import recruit.demo.repository.AppPermissionRepository;
import recruit.demo.repository.AppRoleRepository;
import recruit.demo.security.UserSnapshotCache;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** specs/004-rbac: ma trận đọc từ DB có cache; sửa ma trận xoá cache; không gỡ được role:manage khỏi ADMIN. */
class RbacServiceImplTest {

    private AppRoleRepository roles;
    private AppPermissionRepository perms;
    private UserSnapshotCache userCache;
    private RbacServiceImpl service;
    private final Map<String, AppPermission> catalog = new HashMap<>();

    private AppPermission perm(String code) {
        return catalog.computeIfAbsent(code, c -> new AppPermission(c, c.split(":")[0], c));
    }

    private AppRole role(String code, String... ps) {
        Set<AppPermission> set = new HashSet<>();
        for (String p : ps) set.add(perm(p));
        return new AppRole(code, code, null, set);
    }

    @BeforeEach
    void setUp() {
        roles = mock(AppRoleRepository.class);
        perms = mock(AppPermissionRepository.class);
        userCache = mock(UserSnapshotCache.class);
        service = new RbacServiceImpl(roles, perms, userCache);
        List.of("job:create", "job:update", "role:manage", "user:read").forEach(this::perm);
        when(perms.findAllById(any())).thenAnswer(i -> {
            List<AppPermission> out = new ArrayList<>();
            for (Object c : (Iterable<?>) i.getArgument(0)) if (catalog.containsKey(c)) out.add(catalog.get(c));
            return out;
        });
        when(roles.save(any(AppRole.class))).thenAnswer(i -> i.getArgument(0));
    }

    @Test
    void permissionsAreReadOnceThenCached() {
        when(roles.findById("RECRUITER")).thenReturn(Optional.of(role("RECRUITER", "job:update", "job:create")));
        assertEquals(List.of("job:create", "job:update"), service.permissionsOf(Role.RECRUITER));
        service.permissionsOf(Role.RECRUITER);
        verify(roles, times(1)).findById("RECRUITER");
    }

    @Test
    void updateReplacesPermissionsAndClearsCaches() {
        AppRole recruiter = role("RECRUITER", "job:create", "job:update");
        when(roles.findById("RECRUITER")).thenReturn(Optional.of(recruiter));
        service.permissionsOf(Role.RECRUITER);

        var dto = service.updateRolePermissions("recruiter", List.of("job:create"));

        assertEquals(List.of("job:create"), dto.getPermissions());
        verify(userCache).evictAll();
        assertEquals(List.of("job:create"), service.permissionsOf(Role.RECRUITER));
        verify(roles, times(3)).findById("RECRUITER"); // cache xoá nên đọc lại
    }

    @Test
    void cannotRemoveRoleManageFromAdmin() {
        when(roles.findById("ADMIN")).thenReturn(Optional.of(role("ADMIN", "role:manage", "user:read")));
        assertThrows(BusinessException.class, () -> service.updateRolePermissions("ADMIN", List.of("user:read")));
        verify(roles, never()).save(any());
        verify(userCache, never()).evictAll();
    }

    @Test
    void unknownPermissionIsRejected() {
        when(roles.findById("CANDIDATE")).thenReturn(Optional.of(role("CANDIDATE")));
        BusinessException ex = assertThrows(BusinessException.class,
                () -> service.updateRolePermissions("CANDIDATE", List.of("job:create", "nope:x")));
        assertTrue(ex.getMessage().contains("nope:x"));
        verify(roles, never()).save(any());
    }
}
