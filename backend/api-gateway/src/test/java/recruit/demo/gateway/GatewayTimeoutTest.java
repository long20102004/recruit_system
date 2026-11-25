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

import static org.junit.jupiter.api.Assertions.*;

/** spring.http.clients.read-timeout áp dụng cho lời gọi từ gateway tới service (mặc định 240s cho lời gọi AI). */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "spring.http.clients.read-timeout=500ms")
class GatewayTimeoutTest {

    private static final HttpServer SLOW = slowServer();

    @LocalServerPort
    int port;

    @DynamicPropertySource
    static void targets(DynamicPropertyRegistry r) {
        r.add("RECRUITMENT_URL", () -> "http://localhost:" + SLOW.getAddress().getPort());
    }

    @AfterAll
    static void stop() {
        SLOW.stop(0);
    }

    @Test
    void readTimeoutIsApplied() throws Exception {
        long start = System.nanoTime();
        HttpResponse<String> res = HttpClient.newHttpClient().send(
                HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/api/jobs")).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        long ms = (System.nanoTime() - start) / 1_000_000;
        assertTrue(res.statusCode() >= 500, "status " + res.statusCode());
        assertTrue(ms < 2500, "took " + ms + "ms");
    }

    private static HttpServer slowServer() {
        try {
            HttpServer s = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
            s.setExecutor(java.util.concurrent.Executors.newCachedThreadPool());
            s.createContext("/", ex -> {
                try { Thread.sleep(3000); } catch (InterruptedException ignored) { Thread.currentThread().interrupt(); }
                ex.sendResponseHeaders(200, -1);
                ex.close();
            });
            s.start();
            return s;
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }
}
