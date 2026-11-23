package recruit.demo.security;
import org.junit.jupiter.api.Test;
import recruit.demo.config.AppProperties;
import recruit.demo.entity.*;
import static org.junit.jupiter.api.Assertions.*;
class JwtContractTest {
    @Test void signedIdentityIsPortableAndTamperingIsRejected() {
        AppProperties properties = new AppProperties();
        properties.getJwt().setSecret("test-secret-with-at-least-32-characters-long");
        properties.getJwt().setExpirationMs(60000);
        JwtService issuer = new JwtService(properties);
        JwtService verifier = new JwtService(properties);
        String token = issuer.generateToken(12, "test@example.com", Role.CANDIDATE);
        assertTrue(verifier.isValid(token));
        assertEquals(12, verifier.getUserId(token));
        assertEquals("test@example.com", verifier.getEmail(token));
        assertFalse(verifier.isValid(token.substring(0, 10) + "x" + token.substring(11)));
    }
    @Test void bannedAccountsCannotBeAuthenticated() {
        var user = new UserPrincipal(1, "test@example.com", "", "Test", Role.CANDIDATE, UserStatus.BANNED);
        assertFalse(user.isEnabled());
        assertFalse(user.isAccountNonLocked());
    }
}
