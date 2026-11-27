package recruit.demo.storage;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import java.time.Duration;

/**
 * Cấu hình Cloudflare R2 (specs/008-r2-storage). Thiếu giá trị bắt buộc thì service dừng lúc khởi động.
 * Secret chỉ đến từ biến môi trường, không đặt giá trị thật trong application.yml.
 */
@Data
@Validated
@ConfigurationProperties(prefix = "storage.r2")
public class R2Properties {

    @NotBlank
    private String accountId;

    @NotBlank
    private String accessKeyId;

    @NotBlank
    private String secretAccessKey;

    /** Bucket private: CV PDF, giấy phép công ty. Chỉ truy cập qua presigned URL. */
    @NotBlank
    private String privateBucket;

    /** Bucket đã bật public access: logo, ảnh bìa. */
    @NotBlank
    private String publicBucket;

    /** URL gốc của bucket public, vd https://pub-xxxx.r2.dev hoặc custom domain. */
    @NotBlank
    private String publicBaseUrl;

    /** Ghi đè endpoint S3 (để trống = https://{accountId}.r2.cloudflarestorage.com). */
    private String endpoint;

    @NotNull
    private Duration presignTtl = Duration.ofMinutes(5);

    public String resolvedEndpoint() {
        return endpoint != null && !endpoint.isBlank()
                ? endpoint
                : "https://" + accountId + ".r2.cloudflarestorage.com";
    }
}
