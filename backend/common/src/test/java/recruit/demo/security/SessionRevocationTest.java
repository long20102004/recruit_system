package recruit.demo.security;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.core.context.SecurityContextHolder;
import recruit.demo.config.AppProperties;
import recruit.demo.entity.Role;
import recruit.demo.entity.UserStatus;

import static org.junit.jupiter.api.Assertions.*;

/** specs/003-auth-flow FR-014, FR-017: token phát hành trước mốc vô hiệu phiên bị từ chối ở mọi service. */
class SessionRevocationTest {

    private final JwtService jwt = jwtService();

    @AfterEach
    void clear() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void tokenIssuedBeforeRevocationIsRejected() throws Exception {
        String token = jwt.generateToken(7, "a@x.test", Role.CANDIDATE);
        long issuedAt = jwt.parseClaims(token).getIssuedAt().getTime() / 1000;

        MockHttpServletResponse res = run(token, principal(issuedAt + 5));

        assertEquals(401, res.getStatus());
        assertNull(SecurityContextHolder.getContext().getAuthentication());
    }

    @Test
    void tokenIssuedAfterRevocationIsAccepted() throws Exception {
        String token = jwt.generateToken(7, "a@x.test", Role.CANDIDATE);
        long issuedAt = jwt.parseClaims(token).getIssuedAt().getTime() / 1000;

        MockHttpServletResponse res = run(token, principal(issuedAt));

        assertEquals(200, res.getStatus());
        assertNotNull(SecurityContextHolder.getContext().getAuthentication());
    }

    @Test
    void userWithoutRevocationMarkAcceptsAnyValidToken() {
        var user = new UserPrincipal(7, "a@x.test", "", "A", Role.CANDIDATE, UserStatus.ACTIVE);
        assertTrue(user.acceptsTokenIssuedAt(new java.util.Date(0)));
    }

    private MockHttpServletResponse run(String token, UserPrincipal principal) throws Exception {
        var filter = new JwtAuthenticationFilter(jwt, (id, email) -> principal);
        var req = new MockHttpServletRequest();
        req.addHeader("Authorization", "Bearer " + token);
        var res = new MockHttpServletResponse();
        filter.doFilter(req, res, new MockFilterChain());
        return res;
    }

    private static UserPrincipal principal(long sessionsValidAfter) {
        return new UserPrincipal(7, "a@x.test", "", "A", Role.CANDIDATE, UserStatus.ACTIVE, sessionsValidAfter);
    }

    private static JwtService jwtService() {
        AppProperties p = new AppProperties();
        p.getJwt().setSecret("test-secret-with-at-least-32-characters-long");
        p.getJwt().setExpirationMs(60000);
        return new JwtService(p);
    }
}
