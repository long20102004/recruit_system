package recruit.demo.client;
import org.springframework.stereotype.Component;
import org.springframework.http.HttpStatus;
import recruit.demo.exception.ApiException;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.JsonNode;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
@Component
public class AiJsonClient {
    private final ObjectMapper mapper;
    private final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
    public AiJsonClient(ObjectMapper mapper) { this.mapper = mapper; }
    public JsonNode post(String url, Object body) {
        try {
            var request = HttpRequest.newBuilder(URI.create(url)).timeout(Duration.ofSeconds(180))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body))).build();
            var response = client.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() == 413) throw new ApiException(HttpStatus.PAYLOAD_TOO_LARGE, "CV exceeds model context");
            if (response.statusCode() >= 400) throw new ApiException(HttpStatus.BAD_GATEWAY, "AI service failed (HTTP " + response.statusCode() + ")");
            return mapper.readTree(response.body());
        } catch (ApiException ex) { throw ex;
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt(); throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "AI call interrupted");
        } catch (Exception ex) { throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "AI service unavailable; check model and service URL"); }
    }
}
