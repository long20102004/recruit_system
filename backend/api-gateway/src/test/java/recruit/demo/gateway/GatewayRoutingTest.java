package recruit.demo.gateway;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.*;

/** Gateway chuyển đúng route tới từng service (stub), giữ nguyên path, query, header, body; chặn đường dẫn lạ. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class GatewayRoutingTest {

    private static final HttpServer IDENTITY = stub("identity");
    private static final HttpServer RECRUITMENT = stub("recruitment");
    private static final HttpServer INTERVIEW = stub("interview");

    @LocalServerPort
    int port;

    private final HttpClient http = HttpClient.newHttpClient();

    @DynamicPropertySource
    static void targets(DynamicPropertyRegistry r) {
        r.add("IDENTITY_URL", () -> url(IDENTITY));
        r.add("RECRUITMENT_URL", () -> url(RECRUITMENT));
        r.add("INTERVIEW_URL", () -> url(INTERVIEW));
    }

    @AfterAll
    static void stop() {
        IDENTITY.stop(0);
        RECRUITMENT.stop(0);
        INTERVIEW.stop(0);
    }

    @Test
    void routesEachPrefixToItsService() throws Exception {
        assertEquals("identity GET /api/auth/me", get("/api/auth/me").body());
        assertEquals("identity GET /api/admin/users?q=a", get("/api/admin/users?q=a").body());
        assertEquals("identity GET /api/admin/roles", get("/api/admin/roles").body());
        assertEquals("recruitment GET /api/jobs", get("/api/jobs").body());
        assertEquals("recruitment GET /api/jobs/3", get("/api/jobs/3").body());
        assertEquals("recruitment GET /api/applications/mine", get("/api/applications/mine").body());
        assertEquals("interview GET /api/interviews/sessions/mine", get("/api/interviews/sessions/mine").body());
    }

    @Test
    void forwardsAuthorizationHeaderAndBody() throws Exception {
        HttpResponse<String> res = http.send(HttpRequest.newBuilder(URI.create(base() + "/api/cvs/upload"))
                .header("Authorization", "Bearer abc")
                .header("Content-Type", "multipart/form-data; boundary=XyZ")
                .POST(HttpRequest.BodyPublishers.ofString("--XyZ\r\nhello\r\n--XyZ--\r\n"))
                .build(), HttpResponse.BodyHandlers.ofString());
        assertEquals("recruitment POST /api/cvs/upload auth=Bearer abc body=--XyZ\r\nhello\r\n--XyZ--\r\n", res.body());
    }

    @Test
    void passesThroughDownstreamStatus() throws Exception {
        assertEquals(401, get("/api/auth/status401").statusCode());
    }

    @Test
    void unknownAndInternalPathsAreNotRouted() throws Exception {
        assertEquals(404, get("/internal/users/1").statusCode());
        assertEquals(404, get("/api/unknown").statusCode());
        assertEquals(200, get("/health").statusCode());
    }

    private HttpResponse<String> get(String path) throws Exception {
        return http.send(HttpRequest.newBuilder(URI.create(base() + path)).GET().build(),
                HttpResponse.BodyHandlers.ofString());
    }

    private String base() {
        return "http://localhost:" + port;
    }

    private static String url(HttpServer s) {
        return "http://localhost:" + s.getAddress().getPort();
    }

    /** Trả "<tên> <method> <path?query>" (+ header Authorization và body nếu có); path chứa "status401" trả 401. */
    private static HttpServer stub(String name) {
        try {
            HttpServer s = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
            s.createContext("/", ex -> {
                String body = new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
                String auth = ex.getRequestHeaders().getFirst("Authorization");
                StringBuilder out = new StringBuilder(name + " " + ex.getRequestMethod() + " " + ex.getRequestURI());
                if (auth != null) out.append(" auth=").append(auth);
                if (!body.isEmpty()) out.append(" body=").append(body);
                byte[] bytes = out.toString().getBytes(StandardCharsets.UTF_8);
                int status = ex.getRequestURI().getPath().contains("status401") ? 401 : 200;
                ex.sendResponseHeaders(status, bytes.length);
                ex.getResponseBody().write(bytes);
                ex.close();
            });
            s.start();
            return s;
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }
}
