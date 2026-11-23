package recruit.demo.security;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;
import recruit.demo.service.ProfileProvisioningService;
import java.io.IOException;
@Component
@RequiredArgsConstructor
public class ProfileProvisioningFilter extends AuthenticatedRequestHook {
    private final ProfileProvisioningService profiles;
    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws IOException, ServletException {
        var auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof UserPrincipal user) profiles.ensureProfile(user);
        chain.doFilter(req, res);
    }
}
