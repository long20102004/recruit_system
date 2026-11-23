package recruit.demo.client;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import recruit.demo.exception.ApiException;
import tools.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
@Component
public class ServiceHttpClient {
    private final ObjectMapper mapper;
    private final String token;
    private final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
    public ServiceHttpClient(ObjectMapper mapper, @Value("${app.services.token}") String token) {
        this.mapper = mapper; this.token = token;
    }
    public <T> T get(String url, Class<T> type) { return exchange("GET", url, null, type); }
    public <T> T patch(String url, Object body, Class<T> type) { return exchange("PATCH", url, body, type); }
    private <T> T exchange(String method, String url, Object body, Class<T> type) {
        try {
            HttpRequest.Builder request = HttpRequest.newBuilder(URI.create(url))
                .timeout(Duration.ofSeconds(10)).header("X-Service-Token", token)
                .header("Content-Type", "application/json");
            request.method(method, body == null ? HttpRequest.BodyPublishers.noBody()
                : HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body)));
            HttpResponse<String> response = client.send(request.build(), HttpResponse.BodyHandlers.ofString());
            if (java.util.Set.of(400, 403, 404, 409, 422).contains(response.statusCode()))
                throw new ApiException(HttpStatus.valueOf(response.statusCode()), "Referenced resource is unavailable or not permitted");
            if (response.statusCode() >= 400) throw new ApiException(HttpStatus.BAD_GATEWAY, "Upstream service rejected request");
            return mapper.readValue(response.body(), type);
        } catch (ApiException ex) { throw ex;
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Service call interrupted");
        } catch (Exception ex) {
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Upstream service unavailable");
        }
    }
}
