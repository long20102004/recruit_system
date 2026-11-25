package recruit.demo.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.RedisConnectionFailureException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import recruit.demo.exception.BusinessException;
import recruit.demo.service.OneTimeTokenService.Purpose;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class OneTimeTokenServiceTest {

    private StringRedisTemplate redis;
    private ValueOperations<String, String> ops;
    private OneTimeTokenService service;

    @BeforeEach
    @SuppressWarnings("unchecked")
    void setUp() {
        redis = mock(StringRedisTemplate.class);
        ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        service = new OneTimeTokenService(redis);
    }

    @Test
    void issueStoresOnlyHashAndRevokesPreviousToken() {
        when(ops.getAndSet(eq("auth:token:reset:user:9"), anyString())).thenReturn("oldhash");

        String raw = service.issue(Purpose.RESET, 9, Duration.ofMinutes(30));

        String hash = OneTimeTokenService.sha256(raw);
        assertNotEquals(raw, hash);
        assertTrue(raw.length() >= 40);
        verify(ops).set("auth:token:reset:" + hash, "9", Duration.ofMinutes(30));
        verify(redis).delete("auth:token:reset:oldhash");
    }

    @Test
    void consumeIsSingleUse() {
        String raw = "abc";
        String key = "auth:token:verify:" + OneTimeTokenService.sha256(raw);
        when(ops.getAndDelete(key)).thenReturn("9").thenReturn(null);

        assertEquals(9, service.consume(Purpose.VERIFY, raw).orElseThrow());
        assertTrue(service.consume(Purpose.VERIFY, raw).isEmpty());
        verify(redis).delete("auth:token:verify:user:9");
    }

    @Test
    void blankOrOversizedTokenIsRejectedWithoutRedis() {
        assertTrue(service.consume(Purpose.VERIFY, " ").isEmpty());
        assertTrue(service.consume(Purpose.VERIFY, "x".repeat(201)).isEmpty());
        verifyNoInteractions(ops);
    }

    @Test
    void redisFailureIsServiceUnavailable() {
        when(ops.getAndDelete(anyString())).thenThrow(new RedisConnectionFailureException("down"));
        BusinessException ex = assertThrows(BusinessException.class, () -> service.consume(Purpose.VERIFY, "abc"));
        assertEquals(503L, ex.getCode());
    }
}
