package recruit.demo.security;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import recruit.demo.dto.ServiceDtos.UserSnapshot;
import recruit.demo.entity.Role;
import recruit.demo.entity.UserStatus;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/**
 * Bản tóm tắt người dùng dùng chung cho mọi service, lưu ở Redis hash {@code auth:user:{id}} có TTL.
 * identity-service xoá key khi trạng thái / vai trò / mốc vô hiệu phiên đổi, nên khoá tài khoản có hiệu lực ngay.
 * Redis lỗi thì coi như trượt cache: người gọi đọc thẳng từ identity-service.
 */
@Slf4j
@Component
public class UserSnapshotCache {

    static final String PREFIX = "auth:user:";

    private final StringRedisTemplate redis;
    private final Duration ttl;

    public UserSnapshotCache(StringRedisTemplate redis,
                             @Value("${app.identity.cache-ttl:60s}") Duration ttl) {
        this.redis = redis;
        this.ttl = ttl;
    }

    public Optional<UserSnapshot> get(Integer userId) {
        try {
            Map<Object, Object> h = redis.opsForHash().entries(PREFIX + userId);
            if (h == null || h.isEmpty()) return Optional.empty();
            return Optional.of(new UserSnapshot(
                    Integer.valueOf((String) h.get("id")),
                    blankToNull(h.get("fullName")),
                    (String) h.get("email"),
                    blankToNull(h.get("phone")),
                    Role.valueOf((String) h.get("role")),
                    UserStatus.valueOf((String) h.get("status")),
                    parseLong(h.get("sessionsValidAfter"))));
        } catch (RuntimeException ex) {
            log.warn("User cache read failed for {}: {}", userId, ex.getClass().getSimpleName());
            return Optional.empty();
        }
    }

    public void put(UserSnapshot u) {
        try {
            Map<String, String> h = new HashMap<>();
            h.put("id", String.valueOf(u.id()));
            h.put("fullName", nullToBlank(u.fullName()));
            h.put("email", u.email());
            h.put("phone", nullToBlank(u.phone()));
            h.put("role", u.role().name());
            h.put("status", u.status().name());
            h.put("sessionsValidAfter", u.sessionsValidAfter() == null ? "" : String.valueOf(u.sessionsValidAfter()));
            String key = PREFIX + u.id();
            redis.opsForHash().putAll(key, h);
            redis.expire(key, ttl);
        } catch (RuntimeException ex) {
            log.warn("User cache write failed for {}: {}", u.id(), ex.getClass().getSimpleName());
        }
    }

    /** Gọi sau mọi thay đổi trạng thái, vai trò, họ tên, SĐT hoặc mốc vô hiệu phiên. */
    public void evict(Integer userId) {
        try {
            redis.delete(PREFIX + userId);
        } catch (RuntimeException ex) {
            log.warn("User cache evict failed for {}: {}", userId, ex.getClass().getSimpleName());
        }
    }

    private static String nullToBlank(String v) { return v == null ? "" : v; }

    private static String blankToNull(Object v) {
        return v == null || ((String) v).isEmpty() ? null : (String) v;
    }

    private static Long parseLong(Object v) {
        return v == null || ((String) v).isEmpty() ? null : Long.valueOf((String) v);
    }
}
