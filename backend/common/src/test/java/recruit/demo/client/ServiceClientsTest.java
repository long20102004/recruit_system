package recruit.demo.client;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.ImportAutoConfiguration;
import org.springframework.boot.jackson.autoconfigure.JacksonAutoConfiguration;
import org.springframework.boot.http.converter.autoconfigure.HttpMessageConvertersAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.cloud.openfeign.FeignAutoConfiguration;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import recruit.demo.config.ServiceClientsConfig;
import recruit.demo.dto.ServiceDtos.ProfileUpdate;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
import recruit.demo.exception.ApiException;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ConcurrentHashMap;

import static org.junit.jupiter.api.Assertions.*;

/** Feign client giữa các service: token nội bộ, PATCH, query tuỳ chọn, ánh xạ lỗi như ServiceHttpClient cũ. */
@SpringBootTest(classes = ServiceClientsTest.TestConfig.class, webEnvironment = SpringBootTest.WebEnvironment.NONE)
class ServiceClientsTest {

    @Configuration
    @Import(ServiceClientsConfig.class)
    @ImportAutoConfiguration({JacksonAutoConfiguration.class, HttpMessageConvertersAutoConfiguration.class,
            FeignAutoConfiguration.class})
    static class TestConfig {
    }

    /** Lần gọi gần nhất: method, path?query, header token, body. */
    static final ConcurrentHashMap<String, String> LAST = new ConcurrentHashMap<>();
    static final HttpServer SERVER = server();

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        String base = "http://localhost:" + SERVER.getAddress().getPort();
        r.add("app.services.identity-url", () -> base);
        r.add("app.services.recruitment-url", () -> base);
        r.add("app.services.interview-url", () -> base);
        r.add("app.services.token", () -> "svc-token");
    }

    @AfterAll
    static void stop() {
        SERVER.stop(0);
    }

    @Autowired IdentityServiceClient identity;
    @Autowired RecruitmentServiceClient recruitment;
    @Autowired InterviewServiceClient interview;

    @BeforeEach
    void reset() {
        LAST.clear();
    }

    @Test
    void getSendsServiceTokenAndDecodesRecord() {
        var user = identity.getUser(7);
        assertEquals("GET /internal/users/7", LAST.get("req"));
        assertEquals("svc-token", LAST.get("token"));
        assertEquals("a@x.test", user.email());
        assertEquals(Role.CANDIDATE, user.role());
        assertEquals(UserStatus.ACTIVE, user.status());
        assertEquals(1700000000L, user.sessionsValidAfter());
    }

    @Test
    void patchSendsJsonBody() {
        identity.updateUser(7, new ProfileUpdate("An", null));
        assertEquals("PATCH /internal/users/7", LAST.get("req"));
        assertTrue(LAST.get("body").contains("\"fullName\":\"An\""), LAST.get("body"));
    }

    @Test
    void nullQueryParamsAreOmitted() {
        recruitment.interviewContext(10, null, 5);
        assertEquals("GET /internal/interview-context?userId=10&applicationId=5", LAST.get("req"));
        assertEquals(3, interview.questionCount().count());
    }

    @Test
    void clientErrorsKeepStatusOtherErrorsBecomeBadGateway() {
        assertEquals(404, assertThrows(ApiException.class, () -> identity.getUser(404)).getStatus().value());
        assertEquals(403, assertThrows(ApiException.class, () -> identity.getUser(403)).getStatus().value());
        assertEquals(502, assertThrows(ApiException.class, () -> identity.getUser(500)).getStatus().value());
        assertEquals(502, assertThrows(ApiException.class, () -> identity.getUser(401)).getStatus().value());
    }

    @Test
    void unreadableBodyIsServiceUnavailable() {
        assertEquals(503, assertThrows(ApiException.class, () -> identity.getUser(999)).getStatus().value());
    }

    private static HttpServer server() {
        try {
            HttpServer s = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
            s.createContext("/", ex -> {
                String body = new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
                LAST.put("req", ex.getRequestMethod() + " " + ex.getRequestURI());
                LAST.put("token", String.valueOf(ex.getRequestHeaders().getFirst("X-Service-Token")));
                LAST.put("body", body);
                String path = ex.getRequestURI().getPath();
                int status = 200;
                String out;
                if (path.matches("/internal/users/(404|403|500|401)")) {
                    status = Integer.parseInt(path.substring(path.lastIndexOf('/') + 1));
                    out = "{}";
                } else if (path.equals("/internal/users/999")) {
                    out = "not json";
                } else if (path.startsWith("/internal/users/")) {
                    out = "{\"id\":7,\"fullName\":\"A\",\"email\":\"a@x.test\",\"phone\":null,"
                            + "\"role\":\"CANDIDATE\",\"status\":\"ACTIVE\",\"sessionsValidAfter\":1700000000}";
                } else if (path.equals("/internal/interviews/question-count")) {
                    out = "{\"count\":3}";
                } else {
                    out = "{\"candidateId\":1,\"userId\":10}";
                }
                byte[] bytes = out.getBytes(StandardCharsets.UTF_8);
                ex.getResponseHeaders().add("Content-Type", "application/json");
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
