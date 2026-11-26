package recruit.demo.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.time.Duration;

/** Cấu hình luồng xác thực (specs/003-auth-flow). */
@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "app.auth")
public class AuthProperties {
    /** Gốc URL giao diện web, dùng tạo link trong email. */
    private String frontendUrl = "http://localhost:5173";
    /** OAuth Client ID (Web) của Google; rỗng = tắt đăng nhập Google. */
    private String googleClientId = "";
    /** JWKS của Google để xác minh chữ ký ID token. */
    private String googleJwksUri = "https://www.googleapis.com/oauth2/v3/certs";
    private String mailFrom = "HireLens <no-reply@hirelens.local>";
    private Duration verifyTokenTtl = Duration.ofHours(24);
    private Duration resetTokenTtl = Duration.ofMinutes(30);
    /** Giãn cách tối thiểu giữa hai lần gửi mail cùng loại cho một email. */
    private Duration resendCooldown = Duration.ofSeconds(60);
    private int maxFailedLogins = 5;
    private Duration failedLoginWindow = Duration.ofMinutes(15);
    private Duration loginLockDuration = Duration.ofMinutes(15);
}
