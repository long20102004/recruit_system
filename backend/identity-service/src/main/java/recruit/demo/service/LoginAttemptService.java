package recruit.demo.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import recruit.demo.config.AuthProperties;

import java.util.Optional;
import java.util.concurrent.TimeUnit;

/**
 * Đếm đăng nhập sai theo email trong Redis; đủ ngưỡng thì khoá tạm.
 * Redis lỗi → bỏ qua (fail-open) để đăng nhập vẫn chạy, chỉ ghi log cảnh báo.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class LoginAttemptService {

    private final StringRedisTemplate redis;
    private final AuthProperties props;

    /** Số giây còn khoá tạm, rỗng nếu không bị khoá. */
    public Optional<Long> lockedForSeconds(String email) {
        try {
            Long ttl = redis.getExpire(lockKey(email), TimeUnit.SECONDS);
            return ttl != null && ttl > 0 ? Optional.of(ttl) : Optional.empty();
        } catch (RuntimeException ex) {
            warn(ex);
            return Optional.empty();
        }
    }

    /** Ghi nhận một lần sai; trả true nếu lần này làm email bị khoá tạm. */
    public boolean recordFailure(String email) {
        try {
            String failKey = failKey(email);
            Long count = redis.opsForValue().increment(failKey);
            if (count != null && count == 1) redis.expire(failKey, props.getFailedLoginWindow());
            if (count != null && count >= props.getMaxFailedLogins()) {
                redis.opsForValue().set(lockKey(email), "1", props.getLoginLockDuration());
                redis.delete(failKey);
                return true;
            }
            return false;
        } catch (RuntimeException ex) {
            warn(ex);
            return false;
        }
    }

    /** Đăng nhập đúng: xoá bộ đếm sai. */
    public void reset(String email) {
        try {
            redis.delete(failKey(email));
        } catch (RuntimeException ex) {
            warn(ex);
        }
    }

    /** Đặt lại mật khẩu: gỡ cả khoá tạm lẫn bộ đếm. */
    public void clear(String email) {
        try {
            redis.delete(java.util.List.of(failKey(email), lockKey(email)));
        } catch (RuntimeException ex) {
            warn(ex);
        }
    }

    private static String failKey(String email) { return "auth:login:fail:" + email; }

    private static String lockKey(String email) { return "auth:login:lock:" + email; }

    private static void warn(RuntimeException ex) {
        log.warn("Redis unavailable for login attempts, skipping: {}", ex.getClass().getSimpleName());
    }
}
