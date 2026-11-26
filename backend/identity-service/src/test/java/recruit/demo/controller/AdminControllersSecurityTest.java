package recruit.demo.controller;

import recruit.demo.dto.admin.LockRequest;
import recruit.demo.dto.admin.UpdateRolePermissionsRequest;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.core.context.SecurityContextHolder;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
import recruit.demo.security.UserPrincipal;
import recruit.demo.service.AdminUserService;
import recruit.demo.service.RbacService;

import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;

/** @PreAuthorize trên controller admin: thiếu permission → AccessDenied (GlobalExceptionHandler trả 403). */
class AdminControllersSecurityTest {

    @Configuration
    @EnableMethodSecurity
    static class Cfg {
        @Bean AdminUserService adminUserService() { return mock(AdminUserService.class); }
        @Bean RbacService rbacService() { return mock(RbacService.class); }
        @Bean AdminUserController adminUserController(AdminUserService s) { return new AdminUserController(s); }
        @Bean AdminRoleController adminRoleController(RbacService s) { return new AdminRoleController(s); }
    }

    private final AnnotationConfigApplicationContext ctx = new AnnotationConfigApplicationContext(Cfg.class);

    @AfterEach
    void clear() {
        SecurityContextHolder.clearContext();
        ctx.close();
    }

    private static void loginWith(Role role, String... perms) {
        var p = new UserPrincipal(1, "u@x.test", "", "U", role, UserStatus.ACTIVE, null, Set.of(perms));
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(p, null, p.getAuthorities()));
    }

    @Test
    void userAdminEndpointsRequirePermissionsNotRole() {
        var users = ctx.getBean(AdminUserController.class);
        loginWith(Role.ADMIN, "user:read");
        assertDoesNotThrow(() -> users.list(null, null, 0, 20));
        assertThrows(AccessDeniedException.class, () -> users.lock(5, new LockRequest("x")));

        loginWith(Role.RECRUITER, "job:create");
        assertThrows(AccessDeniedException.class, () -> users.list(null, null, 0, 20));
    }

    @Test
    void roleMatrixRequiresRoleManage() {
        var rolesApi = ctx.getBean(AdminRoleController.class);
        loginWith(Role.ADMIN, "user:read");
        assertThrows(AccessDeniedException.class, rolesApi::matrix);
        loginWith(Role.ADMIN, "role:manage");
        assertDoesNotThrow(rolesApi::matrix);
        assertDoesNotThrow(() -> rolesApi.update("RECRUITER", new UpdateRolePermissionsRequest(List.of())));
    }
}
