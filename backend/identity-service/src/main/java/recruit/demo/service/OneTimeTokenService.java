package recruit.demo.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import recruit.demo.exception.BusinessException;
import recruit.demo.exception.ErrorCode;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Duration;
import java.util.Base64;
import java.util.HexFormat;
import java.util.Optional;

/**
 * Token dùng một lần (xác thực email, đặt lại mật khẩu) lưu ở Redis dạng SHA-256, tự hết hạn.
 * Cấp token mới làm token cũ cùng loại của user đó hết hiệu lực. Redis lỗi → 503.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class OneTimeTokenService {

    public enum Purpose {
        VERIFY("verify"), RESET("reset");
        final String key;
        Purpose(String key) { this.key = key; }
    }

    private static final SecureRandom RANDOM = new SecureRandom();

    private final StringRedisTemplate redis;

    /** Trả token gốc để đặt vào link; máy chủ chỉ giữ bản băm. */
    public String issue(Purpose purpose, Integer userId, Duration ttl) {
        byte[] bytes = new byte[32];
        RANDOM.nextBytes(bytes);
        String raw = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
        String hash = sha256(raw);
        try {
            String userKey = userKey(purpose, userId);
            String previous = redis.opsForValue().getAndSet(userKey, hash);
            if (previous != null) redis.delete(tokenKey(purpose, previous));
            redis.expire(userKey, ttl);
            redis.opsForValue().set(tokenKey(purpose, hash), String.valueOf(userId), ttl);
        } catch (RuntimeException ex) {
            throw unavailable(ex);
        }
        return raw;
    }

    /** Dùng token đúng một lần; trả userId nếu token hợp lệ và còn hạn. */
    public Optional<Integer> consume(Purpose purpose, String raw) {
        if (raw == null || raw.isBlank() || raw.length() > 200) return Optional.empty();
        String hash = sha256(raw);
        try {
            String userId = redis.opsForValue().getAndDelete(tokenKey(purpose, hash));
            if (userId == null) return Optional.empty();
            redis.delete(userKey(purpose, Integer.valueOf(userId)));
            return Optional.of(Integer.valueOf(userId));
        } catch (RuntimeException ex) {
            throw unavailable(ex);
        }
    }

    /** true nếu được phép gửi mail lúc này (chưa gửi trong khoảng giãn cách). */
    public boolean tryAcquireCooldown(Purpose purpose, String email, Duration cooldown) {
        try {
            Boolean ok = redis.opsForValue().setIfAbsent("auth:cooldown:" + purpose.key + ":" + email, "1", cooldown);
            return Boolean.TRUE.equals(ok);
        } catch (RuntimeException ex) {
            throw unavailable(ex);
        }
    }

    private static String tokenKey(Purpose purpose, String hash) {
        return "auth:token:" + purpose.key + ":" + hash;
    }

    private static String userKey(Purpose purpose, Integer userId) {
        return "auth:token:" + purpose.key + ":user:" + userId;
    }

    static String sha256(String raw) {
        try {
            byte[] d = MessageDigest.getInstance("SHA-256").digest(raw.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(d);
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException(ex);
        }
    }

    private static BusinessException unavailable(RuntimeException ex) {
        log.warn("Redis unavailable for one-time token: {}", ex.getClass().getSimpleName());
        return new BusinessException(ErrorCode.SERVICE_UNAVAILABLE,
                "Chức năng tạm thời không khả dụng, vui lòng thử lại sau", null);
    }
}
