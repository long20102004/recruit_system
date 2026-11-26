package recruit.demo.security;

import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import recruit.demo.enums.Role;
import recruit.demo.exception.ApiException;

public final class SecurityUtils {

    private SecurityUtils() {
    }

    public static UserPrincipal currentUser() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !(auth.getPrincipal() instanceof UserPrincipal principal)) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "Not authenticated");
        }
        return principal;
    }

    /** true nếu user hiện tại có permission (ma trận RBAC). Dùng cho điều kiện trong service; chặn endpoint dùng @PreAuthorize. */
    public static boolean hasPermission(String permission) {
        return currentUser().hasPermission(permission);
    }

    /** @deprecated dùng @PreAuthorize("hasAuthority('…')") ở controller (specs/004-rbac). */
    @Deprecated
    public static void requireRole(Role... roles) {
        UserPrincipal user = currentUser();
        for (Role role : roles) {
            if (user.getRole() == role) {
                return;
            }
        }
        throw new ApiException(HttpStatus.FORBIDDEN, "Insufficient role");
    }
}
