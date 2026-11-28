package recruit.demo.controller;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.CacheControl;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;
import recruit.demo.exception.ApiException;
import recruit.demo.security.SecurityUtils;
import tools.jackson.databind.ObjectMapper;

@RestController
public class InterviewSpeechController {
    private final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
    private final ObjectMapper mapper;
    private final StringRedisTemplate redis;
    private final String apiKey;

    public InterviewSpeechController(ObjectMapper mapper, StringRedisTemplate redis,
            @Value("${DEEPGRAM_API_KEY:}") String apiKey) {
        this.mapper = mapper;
        this.redis = redis;
        this.apiKey = apiKey.trim();
    }

    @PostMapping("/api/interviews/speech/token")
    @PreAuthorize("hasAuthority('interview:practice')")
    public ResponseEntity<SpeechToken> token() {
        if (apiKey.isEmpty()) {
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Chưa cấu hình Deepgram cho luyện phỏng vấn.");
        }

        String key = "interview:speech:grant:" + SecurityUtils.currentUser().getId();
        if (!Boolean.TRUE.equals(redis.opsForValue().setIfAbsent(key, "1", Duration.ofSeconds(5)))) {
            throw new ApiException(HttpStatus.TOO_MANY_REQUESTS, "Vui lòng đợi vài giây rồi bật micro lại.");
        }

        var request = HttpRequest.newBuilder(URI.create("https://api.deepgram.com/v1/auth/grant"))
                .timeout(Duration.ofSeconds(10))
                .header("Authorization", "Token " + apiKey)
                .POST(HttpRequest.BodyPublishers.noBody())
                .build();

        try {
            var response = client.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) throw unavailable();
            String token = mapper.readTree(response.body()).path("access_token").asText("");
            if (token.isBlank()) throw unavailable();
            return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(new SpeechToken(token));
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw unavailable();
        } catch (IOException | tools.jackson.core.JacksonException ex) {
            throw unavailable();
        }
    }

    private ApiException unavailable() {
        return new ApiException(HttpStatus.BAD_GATEWAY, "Không lấy được phiên Deepgram. Kiểm tra API key và quyền Member.");
    }

    public record SpeechToken(String accessToken) {}
}
