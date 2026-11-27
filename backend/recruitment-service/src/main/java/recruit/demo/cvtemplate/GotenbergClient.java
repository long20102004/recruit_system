package recruit.demo.cvtemplate;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import recruit.demo.exception.ApiException;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.UUID;

/** Client gọi Gotenberg ({@code POST /forms/libreoffice/convert}) để chuyển {@code .docx} sang PDF. */
@Slf4j
@Component
public class GotenbergClient {

    private static final String CONVERT_PATH = "/forms/libreoffice/convert";
    private static final String DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

    private final String baseUrl;
    private final long timeoutMs;
    private final HttpClient httpClient;

    public GotenbergClient(
            @Value("${app.gotenberg.base-url:http://localhost:3100}") String baseUrl,
            @Value("${app.gotenberg.timeout-ms:20000}") long timeoutMs
    ) {
        this.baseUrl = trimTrailingSlash(baseUrl);
        this.timeoutMs = Math.max(1000L, timeoutMs);
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofMillis(Math.min(this.timeoutMs, 5000L)))
                .build();
    }

    public byte[] convertDocxToPdf(byte[] docxBytes) {
        if (docxBytes == null || docxBytes.length == 0) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "File DOCX rỗng, không thể chuyển PDF");
        }
        String boundary = "----HireLensGotenberg" + UUID.randomUUID().toString().replace("-", "");
        byte[] multipartBody = buildMultipartBody(boundary, docxBytes);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + CONVERT_PATH))
                .timeout(Duration.ofMillis(timeoutMs))
                .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                .POST(HttpRequest.BodyPublishers.ofByteArray(multipartBody))
                .build();

        try {
            HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
            if (response.statusCode() >= 200 && response.statusCode() < 300
                    && response.body() != null && response.body().length > 0) {
                return response.body();
            }
            log.warn("Gotenberg trả HTTP {} khi chuyển DOCX sang PDF", response.statusCode());
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Chuyển đổi chưa sẵn sàng");
        } catch (ApiException ex) {
            throw ex;
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Chuyển đổi chưa sẵn sàng");
        } catch (IOException ex) {
            log.warn("Không kết nối được Gotenberg ({}): {}", baseUrl, ex.getMessage());
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Chuyển đổi chưa sẵn sàng");
        }
    }

    private static byte[] buildMultipartBody(String boundary, byte[] docxBytes) {
        try (ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            String header = "--" + boundary + "\r\n"
                    + "Content-Disposition: form-data; name=\"files\"; filename=\"cv.docx\"\r\n"
                    + "Content-Type: " + DOCX_MIME + "\r\n\r\n";
            String footer = "\r\n--" + boundary + "--\r\n";
            out.write(header.getBytes(StandardCharsets.UTF_8));
            out.write(docxBytes);
            out.write(footer.getBytes(StandardCharsets.UTF_8));
            return out.toByteArray();
        } catch (IOException ex) {
            throw new IllegalStateException(ex);
        }
    }

    private static String trimTrailingSlash(String url) {
        if (url == null || url.isBlank()) {
            return "http://localhost:3100";
        }
        String trimmed = url.trim();
        while (trimmed.endsWith("/")) {
            trimmed = trimmed.substring(0, trimmed.length() - 1);
        }
        return trimmed;
    }
}
