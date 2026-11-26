package recruit.demo.service.impl;

import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import recruit.demo.exception.BusinessException;

import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.interfaces.RSAPublicKey;
import java.util.Date;

import static org.junit.jupiter.api.Assertions.*;

/** specs/005-google-login FR-002: chữ ký, iss, aud, exp của ID token Google. */
class GoogleTokenVerifierImplTest {

    private static final String CLIENT_ID = "test-client.apps.googleusercontent.com";
    private static final KeyPair KEYS = keys();

    private static KeyPair keys() {
        try {
            KeyPairGenerator g = KeyPairGenerator.getInstance("RSA");
            g.initialize(2048);
            return g.generateKeyPair();
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    private static String token(String iss, String aud, long expInSeconds, Object emailVerified, KeyPair signer) throws Exception {
        JWTClaimsSet claims = new JWTClaimsSet.Builder()
                .issuer(iss).audience(aud).subject("google-sub-1")
                .claim("email", "a@gmail.com").claim("email_verified", emailVerified).claim("name", "An Nguyen")
                .issueTime(new Date()).expirationTime(new Date(System.currentTimeMillis() + expInSeconds * 1000))
                .build();
        SignedJWT jwt = new SignedJWT(new JWSHeader(JWSAlgorithm.RS256), claims);
        jwt.sign(new RSASSASigner(signer.getPrivate()));
        return jwt.serialize();
    }

    private static GoogleTokenVerifierImpl verifier(String clientId) {
        return new GoogleTokenVerifierImpl(clientId,
                () -> NimbusJwtDecoder.withPublicKey((RSAPublicKey) KEYS.getPublic()).build());
    }

    @Test
    void validTokenIsAccepted() throws Exception {
        var id = verifier(CLIENT_ID).verify(token("https://accounts.google.com", CLIENT_ID, 600, true, KEYS));
        assertEquals("google-sub-1", id.subject());
        assertEquals("a@gmail.com", id.email());
        assertTrue(id.emailVerified());
        assertEquals("An Nguyen", id.name());
        assertTrue(verifier(CLIENT_ID).verify(token("accounts.google.com", CLIENT_ID, 600, "true", KEYS)).emailVerified());
    }

    @Test
    void wrongAudienceIssuerExpiryOrSignatureAreRejected() throws Exception {
        assertInvalid(token("https://accounts.google.com", "other-app", 600, true, KEYS));
        assertInvalid(token("https://evil.example", CLIENT_ID, 600, true, KEYS));
        assertInvalid(token("https://accounts.google.com", CLIENT_ID, -600, true, KEYS));
        assertInvalid(token("https://accounts.google.com", CLIENT_ID, 600, true, keys()));
        assertInvalid("not-a-jwt");
    }

    @Test
    void notConfiguredIsServiceUnavailable() throws Exception {
        BusinessException ex = assertThrows(BusinessException.class,
                () -> verifier("").verify(token("https://accounts.google.com", CLIENT_ID, 600, true, KEYS)));
        assertEquals(503L, ex.getCode());
    }

    private static void assertInvalid(String token) {
        BusinessException ex = assertThrows(BusinessException.class, () -> verifier(CLIENT_ID).verify(token));
        assertEquals(2008L, ex.getCode());
    }
}
