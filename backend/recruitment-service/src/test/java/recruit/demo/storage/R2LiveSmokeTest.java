package recruit.demo.storage;

import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

/**
 * Kiểm tra với bucket R2 thật (specs/008-r2-storage). Bỏ qua khi chưa đặt R2_ACCOUNT_ID.
 * Ghi object test dưới prefix cvs/0/0 và companies/0, xoá ngay sau khi kiểm.
 */
class R2LiveSmokeTest {

    private static String env(String name) {
        return System.getenv(name);
    }

    @Test
    void putPresignPublicAndDeleteAgainstRealBuckets() throws Exception {
        assumeTrue(env("R2_ACCOUNT_ID") != null && !env("R2_ACCOUNT_ID").isBlank(), "R2_ACCOUNT_ID chưa đặt");
        R2Properties p = new R2Properties();
        p.setAccountId(env("R2_ACCOUNT_ID"));
        p.setAccessKeyId(env("R2_ACCESS_KEY_ID"));
        p.setSecretAccessKey(env("R2_SECRET_ACCESS_KEY"));
        p.setPrivateBucket(env("R2_PRIVATE_BUCKET"));
        p.setPublicBucket(env("R2_PUBLIC_BUCKET"));
        p.setPublicBaseUrl(env("R2_PUBLIC_BASE_URL"));
        R2StorageService storage = new R2StorageService(p);
        HttpClient http = HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NORMAL).build();
        byte[] body = ("smoke " + UUID.randomUUID()).getBytes(StandardCharsets.UTF_8);

        String privateKey = "cvs/0/0/smoke-" + UUID.randomUUID() + ".pdf";
        String publicKey = "companies/0/logo/smoke-" + UUID.randomUUID() + ".png";
        try {
            storage.putPrivate(privateKey, body, "application/pdf");
            var link = storage.presignGet(privateKey, "Thử nghiệm.pdf", false);
            var signed = http.send(HttpRequest.newBuilder(URI.create(link.getUrl())).build(),
                    HttpResponse.BodyHandlers.ofByteArray());
            assertEquals(200, signed.statusCode(), "GET presigned private");
            assertArrayEquals(body, signed.body());
            assertTrue(signed.headers().firstValue("content-disposition").orElse("").startsWith("attachment;"));

            String unsignedUrl = link.getUrl().substring(0, link.getUrl().indexOf('?'));
            int unsigned = http.send(HttpRequest.newBuilder(URI.create(unsignedUrl)).build(),
                    HttpResponse.BodyHandlers.discarding()).statusCode();
            assertTrue(unsigned == 400 || unsigned == 401 || unsigned == 403, "private không ký phải bị chặn: " + unsigned);

            storage.putPublic(publicKey, body, "image/png");
            var pub = http.send(HttpRequest.newBuilder(URI.create(storage.publicUrl(publicKey))).build(),
                    HttpResponse.BodyHandlers.ofByteArray());
            assertEquals(200, pub.statusCode(), "GET public URL");
            assertArrayEquals(body, pub.body());
        } finally {
            storage.deletePrivateQuietly(privateKey);
            storage.deletePublicQuietly(publicKey);
        }

        var afterDelete = storage.presignGet(privateKey, "x.pdf", false);
        assertEquals(404, http.send(HttpRequest.newBuilder(URI.create(afterDelete.getUrl())).build(),
                HttpResponse.BodyHandlers.discarding()).statusCode(), "object đã bị xoá");
    }
}
