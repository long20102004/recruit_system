package recruit.demo.security;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
@Component
public class InternalAccessFilter extends OncePerRequestFilter {
    private final byte[] secret;
    public InternalAccessFilter(@Value("${app.services.token}") String token) {
        if (token.isBlank()) throw new IllegalArgumentException("Service token must not be blank");
        secret = token.getBytes(StandardCharsets.UTF_8);
    }
    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        if (req.getServletPath().startsWith("/internal/")) {
            String supplied = req.getHeader("X-Service-Token");
            if (supplied == null || !MessageDigest.isEqual(secret, supplied.getBytes(StandardCharsets.UTF_8))) {
                res.sendError(401); return;
            }
        }
        chain.doFilter(req, res);
    }
}
