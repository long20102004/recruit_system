package recruit.demo.security;

import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import recruit.demo.entity.Role;
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
