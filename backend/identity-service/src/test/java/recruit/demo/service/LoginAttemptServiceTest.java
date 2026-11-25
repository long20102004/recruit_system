package recruit.demo.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.RedisConnectionFailureException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import recruit.demo.config.AuthProperties;

import java.time.Duration;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class LoginAttemptServiceTest {

    private StringRedisTemplate redis;
    private ValueOperations<String, String> ops;
    private LoginAttemptService service;

    @BeforeEach
    @SuppressWarnings("unchecked")
    void setUp() {
        redis = mock(StringRedisTemplate.class);
        ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        service = new LoginAttemptService(redis, new AuthProperties());
    }

    @Test
    void firstFailureStartsWindow() {
        when(ops.increment("auth:login:fail:a@x.test")).thenReturn(1L);
        assertFalse(service.recordFailure("a@x.test"));
        verify(redis).expire("auth:login:fail:a@x.test", Duration.ofMinutes(15));
        verify(ops, never()).set(eq("auth:login:lock:a@x.test"), anyString(), any(Duration.class));
    }

    @Test
    void fifthFailureLocksForFifteenMinutes() {
        when(ops.increment("auth:login:fail:a@x.test")).thenReturn(5L);
        assertTrue(service.recordFailure("a@x.test"));
        verify(ops).set("auth:login:lock:a@x.test", "1", Duration.ofMinutes(15));
        verify(redis).delete("auth:login:fail:a@x.test");
    }

    @Test
    void reportsRemainingLockSeconds() {
        when(redis.getExpire("auth:login:lock:a@x.test", TimeUnit.SECONDS)).thenReturn(600L);
        assertEquals(600L, service.lockedForSeconds("a@x.test").orElseThrow());
        when(redis.getExpire("auth:login:lock:b@x.test", TimeUnit.SECONDS)).thenReturn(-2L);
        assertTrue(service.lockedForSeconds("b@x.test").isEmpty());
    }

    @Test
    void redisFailureFailsOpen() {
        when(redis.getExpire(anyString(), any(TimeUnit.class))).thenThrow(new RedisConnectionFailureException("down"));
        when(ops.increment(anyString())).thenThrow(new RedisConnectionFailureException("down"));
        assertTrue(service.lockedForSeconds("a@x.test").isEmpty());
        assertFalse(service.recordFailure("a@x.test"));
    }
}
