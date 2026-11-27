package recruit.demo.storage;

import org.junit.jupiter.api.Test;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;

import static org.junit.jupiter.api.Assertions.*;

/** Presign chạy offline (không gọi mạng), dùng key giả. */
class R2StorageServiceTest {

    private R2Properties props() {
        R2Properties p = new R2Properties();
        p.setAccountId("acc123");
        p.setAccessKeyId("AKIDTEST");
        p.setSecretAccessKey("secret-test");
        p.setPrivateBucket("hl-private");
        p.setPublicBucket("hl-public");
        p.setPublicBaseUrl("https://pub-test.r2.dev/");
        p.setPresignTtl(Duration.ofMinutes(5));
        return p;
    }

    @Test
    void presignTargetsPrivateBucketWithExpiryAndDisposition() {
        var service = new R2StorageService(props());
        Instant before = Instant.now();

        var link = service.presignGet("cvs/7/2/abc.pdf", "CV Nguyễn A.pdf", false);
        String url = URLDecoder.decode(link.getUrl(), StandardCharsets.UTF_8);

        assertTrue(url.startsWith("https://acc123.r2.cloudflarestorage.com/hl-private/cvs/7/2/abc.pdf?"), url);
        assertTrue(url.contains("X-Amz-Expires=300"), url);
        assertTrue(url.contains("response-content-disposition=attachment;"), url);
        assertTrue(url.contains("filename*=UTF-8''CV%20Nguy%E1%BB%85n%20A.pdf"), url);
        assertFalse(url.contains("secret-test"));
        assertTrue(link.getExpiresAt().isAfter(before.plusSeconds(290)));
    }

    @Test
    void publicUrlJoinsBaseAndKey() {
        var service = new R2StorageService(props());
        assertEquals("https://pub-test.r2.dev/companies/5/logo/x.png", service.publicUrl("companies/5/logo/x.png"));
        assertNull(service.publicUrl(null));
        assertNull(service.publicUrl(""));
    }

    @Test
    void contentDispositionHasAsciiFallback() {
        assertEquals("inline; filename=\"GPKD_c_ng_ty.pdf\"; filename*=UTF-8''GPKD%20c%C3%B4ng%20ty.pdf",
                R2StorageService.contentDisposition("GPKD công ty.pdf", true));
    }

    @Test
    void endpointDefaultsToAccountAndCanBeOverridden() {
        R2Properties p = props();
        assertEquals("https://acc123.r2.cloudflarestorage.com", p.resolvedEndpoint());
        p.setEndpoint("https://eu.example");
        assertEquals("https://eu.example", p.resolvedEndpoint());
    }
}
