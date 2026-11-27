package recruit.demo.gateway;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;

/** Kiểm tra route /api/notifications/** và khả năng truyền SSE /api/notifications/stream không buffer qua WebMVC gateway (T001, T013). */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
class NotificationGatewayRouteTest {

    private static final CountDownLatch SSE_ALLOW_SECOND_EVENT = new CountDownLatch(1);
    private static final HttpServer NOTIFICATION = stub();

    @LocalServerPort
    int port;

    private final HttpClient http = HttpClient.newHttpClient();

    @DynamicPropertySource
    static void targets(DynamicPropertyRegistry r) {
        r.add("NOTIFICATION_URL", () -> "http://localhost:" + NOTIFICATION.getAddress().getPort());
    }

    @AfterAll
    static void stop() {
        SSE_ALLOW_SECOND_EVENT.countDown();
        NOTIFICATION.stop(0);
    }

    @Test
    void routesNotificationEndpointsAndForwardsAuthorization() throws Exception {
        HttpResponse<String> listRes = http.send(
                HttpRequest.newBuilder(URI.create(base() + "/api/notifications?unread=true&page=0"))
                        .header("Authorization", "Bearer notif-token")
                        .GET().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(200, listRes.statusCode());
        assertEquals("notification GET /api/notifications?unread=true&page=0 auth=Bearer notif-token", listRes.body());

        HttpResponse<String> readRes = http.send(
                HttpRequest.newBuilder(URI.create(base() + "/api/notifications/12/read"))
                        .POST(HttpRequest.BodyPublishers.noBody())
                        .build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(200, readRes.statusCode());
        assertEquals("notification POST /api/notifications/12/read", readRes.body());
    }

    @Test
    void streamsSseWithoutBufferingUntilUpstreamCloses() throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(base() + "/api/notifications/stream"))
                .header("Authorization", "Bearer sse-token")
                .header("Accept", "text/event-stream")
                .timeout(Duration.ofSeconds(10))
                .GET().build();

        HttpResponse<InputStream> res = http.send(req, HttpResponse.BodyHandlers.ofInputStream());
        assertEquals(200, res.statusCode());
        assertTrue(res.headers().firstValue("Content-Type").orElse("").startsWith("text/event-stream"));

        try (BufferedReader reader = new BufferedReader(new InputStreamReader(res.body(), StandardCharsets.UTF_8))) {
            // Đọc chunk đầu tiên TRƯỚC khi upstream được phép gửi tiếp và đóng stream -> chứng minh không bị buffer.
            assertEquals("event: ping", reader.readLine());
            assertEquals("data: ok", reader.readLine());
            assertEquals("", reader.readLine());

            SSE_ALLOW_SECOND_EVENT.countDown();

            assertEquals("event: notification", reader.readLine());
            assertEquals("data: {\"id\":1}", reader.readLine());
            assertEquals("", reader.readLine());
            assertNull(reader.readLine());
        }
    }

    private String base() {
        return "http://localhost:" + port;
    }

    private static HttpServer stub() {
        try {
            HttpServer s = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
            s.setExecutor(Executors.newCachedThreadPool());
            s.createContext("/", ex -> {
                String path = ex.getRequestURI().getPath();
                String auth = ex.getRequestHeaders().getFirst("Authorization");
                if ("/api/notifications/stream".equals(path)) {
                    ex.getResponseHeaders().set("Content-Type", "text/event-stream;charset=UTF-8");
                    ex.getResponseHeaders().set("Cache-Control", "no-cache");
                    ex.sendResponseHeaders(200, 0);
                    OutputStream os = ex.getResponseBody();
                    os.write("event: ping\ndata: ok\n\n".getBytes(StandardCharsets.UTF_8));
                    os.flush();
                    try {
                        SSE_ALLOW_SECOND_EVENT.await(5, TimeUnit.SECONDS);
                    } catch (InterruptedException ignored) {
                        Thread.currentThread().interrupt();
                    }
                    os.write("event: notification\ndata: {\"id\":1}\n\n".getBytes(StandardCharsets.UTF_8));
                    os.flush();
                    ex.close();
                    return;
                }
                StringBuilder out = new StringBuilder("notification " + ex.getRequestMethod() + " " + ex.getRequestURI());
                if (auth != null) out.append(" auth=").append(auth);
                byte[] bytes = out.toString().getBytes(StandardCharsets.UTF_8);
                ex.sendResponseHeaders(200, bytes.length);
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
