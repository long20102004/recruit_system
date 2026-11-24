package recruit.demo.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;

/** Goi cvmatch qua HTTP, gui header X-Service-Token (cvmatch bat buoc khi CVMATCH_ENV=prod). */
@Component
public class HttpCvMatchClient implements CvMatchApi {
    static final String TOKEN_HEADER = "X-Service-Token";

    private final ObjectMapper mapper;
    private final String baseUrl;
    private final String token;
    private final Duration readTimeout;
    private final HttpClient client;

    public HttpCvMatchClient(ObjectMapper mapper,
                             @Value("${app.cvmatch.base-url}") String baseUrl,
                             @Value("${app.cvmatch.service-token:${app.services.token:}}") String token,
                             @Value("${app.cvmatch.read-timeout-ms:120000}") long readTimeoutMs) {
        this.mapper = mapper;
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.token = token;
        this.readTimeout = Duration.ofMillis(readTimeoutMs);
        this.client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
    }

    @Override public Response postCv(Map<String, Object> cv) { return send("POST", "/cv", cv); }

    @Override public Response deleteCv(String cvId) { return send("DELETE", "/cv/" + enc(cvId), null); }

    @Override public Response postJd(Map<String, Object> jd) { return send("POST", "/jd", jd); }

    @Override public Response patchJdStatus(String jdId, String status) {
        return send("PATCH", "/jd/" + enc(jdId) + "/status", Map.of("status", status));
    }

    @Override public Response matchJd(String jdId, Map<String, Object> body) {
        return send("POST", "/match/jd/" + enc(jdId), body);
    }

    @Override public Response matchCv(String cvId, Map<String, Object> body) {
        return send("POST", "/match/cv/" + enc(cvId), body);
    }

    @Override public Response explainForHr(String runId, String cvId) {
        return send("GET", "/match/" + enc(runId) + "/cv/" + enc(cvId) + "/explain", null);
    }

    @Override public Response explainForCandidate(String runId, String jdId) {
        return send("GET", "/match/" + enc(runId) + "/jd/" + enc(jdId) + "/explain", null);
    }

    @Override public Response health() { return send("GET", "/health", null); }

    private Response send(String method, String path, Object body) {
        try {
            var b = HttpRequest.newBuilder(URI.create(baseUrl + path)).timeout(readTimeout)
                    .header("Accept", "application/json");
            if (token != null && !token.isBlank()) b.header(TOKEN_HEADER, token);
            if (body != null) {
                b.header("Content-Type", "application/json")
                        .method(method, HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body)));
            } else {
                b.method(method, HttpRequest.BodyPublishers.noBody());
            }
            HttpResponse<String> r = client.send(b.build(), HttpResponse.BodyHandlers.ofString());
            return new Response(r.statusCode(), parse(r.body()));
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new CvMatchUnavailableException("cvmatch call interrupted", ex);
        } catch (Exception ex) {
            throw new CvMatchUnavailableException("cvmatch unavailable: " + ex.getClass().getSimpleName(), ex);
        }
    }

    private JsonNode parse(String body) {
        if (body == null || body.isBlank()) return null;
        try {
            return mapper.readTree(body);
        } catch (Exception ex) {            // vd 502 HTML tu proxy: giu ma HTTP, bo body
            return null;
        }
    }

    private static String enc(String s) {
        return URLEncoder.encode(s, StandardCharsets.UTF_8).replace("+", "%20");
    }
}
