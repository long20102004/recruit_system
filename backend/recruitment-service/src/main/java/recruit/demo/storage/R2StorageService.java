package recruit.demo.storage;

import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import recruit.demo.dto.FileLinkDto;
import recruit.demo.exception.ApiException;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.core.checksums.RequestChecksumCalculation;
import software.amazon.awssdk.core.checksums.ResponseChecksumValidation;
import software.amazon.awssdk.core.exception.SdkException;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.S3Configuration;
import software.amazon.awssdk.services.s3.model.DeleteObjectRequest;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.PresignedGetObjectRequest;

import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

/**
 * Cloudflare R2 qua API S3. Checksum đặt WHEN_REQUIRED vì SDK mới mặc định gửi CRC mà R2 chưa hỗ trợ đầy đủ.
 * Không log URL ký hay nội dung file.
 */
@Slf4j
@Service
public class R2StorageService implements StorageService {

    private final R2Properties props;
    private final S3Client client;
    private final S3Presigner presigner;

    public R2StorageService(R2Properties props) {
        this.props = props;
        URI endpoint = URI.create(props.resolvedEndpoint());
        var credentials = StaticCredentialsProvider.create(
                AwsBasicCredentials.create(props.getAccessKeyId(), props.getSecretAccessKey()));
        var s3Config = S3Configuration.builder().pathStyleAccessEnabled(true).build();
        this.client = S3Client.builder()
                .endpointOverride(endpoint)
                .region(Region.of("auto"))
                .credentialsProvider(credentials)
                .serviceConfiguration(s3Config)
                .requestChecksumCalculation(RequestChecksumCalculation.WHEN_REQUIRED)
                .responseChecksumValidation(ResponseChecksumValidation.WHEN_REQUIRED)
                .build();
        this.presigner = S3Presigner.builder()
                .endpointOverride(endpoint)
                .region(Region.of("auto"))
                .credentialsProvider(credentials)
                .serviceConfiguration(s3Config)
                .build();
    }

    @Override
    public void putPrivate(String key, byte[] content, String contentType) {
        put(props.getPrivateBucket(), key, content, contentType);
    }

    @Override
    public void putPublic(String key, byte[] content, String contentType) {
        put(props.getPublicBucket(), key, content, contentType);
    }

    @Override
    public byte[] getPrivate(String key) {
        try {
            return client.getObjectAsBytes(GetObjectRequest.builder()
                            .bucket(props.getPrivateBucket())
                            .key(key)
                            .build())
                    .asByteArray();
        } catch (SdkException ex) {
            log.error("R2 getObject thất bại (bucket={}, key={}): {}", props.getPrivateBucket(), key, ex.getClass().getSimpleName());
            throw new ApiException(HttpStatus.BAD_GATEWAY, "Không đọc được tệp từ kho lưu trữ, vui lòng thử lại.");
        }
    }

    private void put(String bucket, String key, byte[] content, String contentType) {
        try {
            client.putObject(PutObjectRequest.builder()
                            .bucket(bucket)
                            .key(key)
                            .contentType(contentType)
                            .build(),
                    RequestBody.fromBytes(content));
        } catch (SdkException ex) {
            log.error("R2 putObject thất bại (bucket={}, key={}): {}", bucket, key, ex.getClass().getSimpleName());
            throw new ApiException(HttpStatus.BAD_GATEWAY, "Không lưu được tệp lên kho lưu trữ, vui lòng thử lại.");
        }
    }

    @Override
    public FileLinkDto presignGet(String key, String fileName, boolean inline) {
        var get = GetObjectRequest.builder()
                .bucket(props.getPrivateBucket())
                .key(key)
                .responseContentDisposition(contentDisposition(fileName, inline))
                .build();
        PresignedGetObjectRequest signed = presigner.presignGetObject(r -> r
                .signatureDuration(props.getPresignTtl())
                .getObjectRequest(get));
        return FileLinkDto.builder()
                .url(signed.url().toString())
                .expiresAt(signed.expiration())
                .build();
    }

    @Override
    public String publicUrl(String key) {
        if (key == null || key.isBlank()) return null;
        String base = props.getPublicBaseUrl();
        return (base.endsWith("/") ? base : base + "/") + key;
    }

    @Override
    public void deletePrivateQuietly(String key) {
        delete(props.getPrivateBucket(), key);
    }

    @Override
    public void deletePublicQuietly(String key) {
        delete(props.getPublicBucket(), key);
    }

    private void delete(String bucket, String key) {
        if (!ObjectKeys.isObjectKey(key)) return;
        try {
            client.deleteObject(DeleteObjectRequest.builder().bucket(bucket).key(key).build());
        } catch (SdkException ex) {
            log.warn("R2 deleteObject thất bại (bucket={}, key={}): {}", bucket, key, ex.getClass().getSimpleName());
        }
    }

    /** Tên file tiếng Việt: filename ASCII dự phòng + filename* UTF-8 (RFC 6266). */
    static String contentDisposition(String fileName, boolean inline) {
        String name = fileName == null || fileName.isBlank() ? "file" : fileName;
        String ascii = name.replaceAll("[^A-Za-z0-9._-]", "_");
        String encoded = URLEncoder.encode(name, StandardCharsets.UTF_8).replace("+", "%20");
        return (inline ? "inline" : "attachment") + "; filename=\"" + ascii + "\"; filename*=UTF-8''" + encoded;
    }

    @PreDestroy
    void close() {
        presigner.close();
        client.close();
    }
}
