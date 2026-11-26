package recruit.demo.service.impl;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2TokenValidatorResult;
import org.springframework.security.oauth2.jwt.*;
import org.springframework.stereotype.Component;
import recruit.demo.config.AuthProperties;
import recruit.demo.exception.BusinessException;
import recruit.demo.exception.ErrorCode;
import recruit.demo.service.GoogleTokenVerifier;

import java.util.Set;
import java.util.function.Supplier;

/**
 * Xác minh ID token Google: chữ ký theo JWKS của Google, iss là Google, aud chứa Client ID, còn hạn.
 * Không log token (FR-006).
 */
@Slf4j
@Component
public class GoogleTokenVerifierImpl implements GoogleTokenVerifier {

    static final Set<String> ISSUERS = Set.of("accounts.google.com", "https://accounts.google.com");

    private final String clientId;
    private final Supplier<JwtDecoder> decoderFactory;
    private volatile JwtDecoder decoder;

    @Autowired
    public GoogleTokenVerifierImpl(AuthProperties props) {
        this(props.getGoogleClientId(), () -> NimbusJwtDecoder.withJwkSetUri(props.getGoogleJwksUri()).build());
    }

    /** Cho test: truyền decoder dựng sẵn (vd từ khoá công khai tự tạo). */
    GoogleTokenVerifierImpl(String clientId, Supplier<JwtDecoder> decoderFactory) {
        this.clientId = clientId == null ? "" : clientId.trim();
        this.decoderFactory = decoderFactory;
    }

    @Override
    public GoogleIdentity verify(String credential) {
        if (clientId.isEmpty()) {
            throw new BusinessException(ErrorCode.SERVICE_UNAVAILABLE, "Đăng nhập Google chưa được cấu hình", null);
        }
        Jwt jwt;
        try {
            jwt = decoder().decode(credential);
        } catch (JwtException ex) {
            log.info("Google ID token rejected: {}", ex.getClass().getSimpleName());
            throw new BusinessException(ErrorCode.GOOGLE_TOKEN_INVALID);
        }
        Object verified = jwt.getClaims().get("email_verified");
        boolean emailVerified = Boolean.TRUE.equals(verified) || "true".equals(String.valueOf(verified));
        return new GoogleIdentity(jwt.getSubject(), jwt.getClaimAsString("email"), emailVerified,
                jwt.getClaimAsString("name"));
    }

    private JwtDecoder decoder() {
        JwtDecoder d = decoder;
        if (d == null) {
            synchronized (this) {
                if (decoder == null) {
                    JwtDecoder built = decoderFactory.get();
                    if (built instanceof NimbusJwtDecoder nimbus) nimbus.setJwtValidator(validator());
                    decoder = built;
                }
                d = decoder;
            }
        }
        return d;
    }

    OAuth2TokenValidator<Jwt> validator() {
        OAuth2TokenValidator<Jwt> issuer = jwt -> ISSUERS.contains(String.valueOf(jwt.getClaims().get("iss")))
                ? OAuth2TokenValidatorResult.success()
                : OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", "issuer is not Google", null));
        OAuth2TokenValidator<Jwt> audience = jwt -> jwt.getAudience() != null && jwt.getAudience().contains(clientId)
                ? OAuth2TokenValidatorResult.success()
                : OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", "audience mismatch", null));
        return new DelegatingOAuth2TokenValidator<>(new JwtTimestampValidator(), issuer, audience);
    }
}
