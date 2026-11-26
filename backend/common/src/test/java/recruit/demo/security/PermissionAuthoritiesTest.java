package recruit.demo.security;

import org.junit.jupiter.api.Test;
import org.springframework.security.core.GrantedAuthority;
import recruit.demo.dto.ServiceDtos.UserSnapshot;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;

import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/** specs/004-rbac: authorities = ROLE_X + từng permission; constructor cũ không có permission. */
class PermissionAuthoritiesTest {

    @Test
    void authoritiesContainRoleAndPermissions() {
        var p = new UserPrincipal(1, "a@x.test", "", "A", Role.RECRUITER, UserStatus.ACTIVE, null,
                List.of("job:update", "job:create"));
        assertEquals(List.of("ROLE_RECRUITER", "job:create", "job:update"),
                p.getAuthorities().stream().map(GrantedAuthority::getAuthority).toList());
        assertTrue(p.hasPermission("job:create"));
        assertFalse(p.hasPermission("user:lock"));
    }

    @Test
    void legacyConstructorsHaveNoPermissions() {
        var p = new UserPrincipal(1, "a@x.test", "", "A", Role.ADMIN, UserStatus.ACTIVE);
        assertEquals(Set.of(), p.getPermissions());
        var snap = new UserSnapshot(1, "A", "a@x.test", null, Role.ADMIN, UserStatus.ACTIVE);
        assertEquals(List.of(), snap.permissions());
    }
}
