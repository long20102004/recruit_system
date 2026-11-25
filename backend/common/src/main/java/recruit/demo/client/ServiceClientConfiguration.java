package recruit.demo.client;

import feign.Capability;
import feign.Client;
import feign.FeignException;
import feign.InvocationHandlerFactory;
import feign.Request;
import feign.RequestInterceptor;
import feign.codec.ErrorDecoder;
import feign.http2client.Http2Client;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.http.HttpStatus;
import recruit.demo.exception.ApiException;

import java.lang.reflect.InvocationHandler;
import java.net.http.HttpClient;
import java.time.Duration;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/**
 * Cấu hình chung cho Feign client gọi giữa các service Java (đăng ký qua {@code defaultConfiguration},
 * không phải @Configuration để không bị quét toàn cục). Giữ hành vi của ServiceHttpClient trước đây:
 * header X-Service-Token, timeout kết nối 3s / đọc 10s, lỗi map sang {@link ApiException}.
 */
public class ServiceClientConfiguration {

    static final String TOKEN_HEADER = "X-Service-Token";
    /** Lỗi phía service đích mà người gọi cần biết đúng mã (không tồn tại, không có quyền, xung đột…). */
    static final Set<Integer> PASS_THROUGH = Set.of(400, 403, 404, 409, 422);

    @Bean
    RequestInterceptor serviceTokenInterceptor(@Value("${app.services.token}") String token) {
        return template -> template.header(TOKEN_HEADER, token);
    }

    /** java.net.http thay cho HttpURLConnection mặc định (không hỗ trợ PATCH). */
    @Bean
    Client feignClient() {
        return new Http2Client(HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(Duration.ofSeconds(3))
                .build());
    }

    @Bean
    Request.Options feignOptions() {
        return new Request.Options(3, TimeUnit.SECONDS, 10, TimeUnit.SECONDS, true);
    }

    @Bean
    ErrorDecoder serviceErrorDecoder() {
        return (methodKey, response) -> PASS_THROUGH.contains(response.status())
                ? new ApiException(HttpStatus.valueOf(response.status()), "Referenced resource is unavailable or not permitted")
                : new ApiException(HttpStatus.BAD_GATEWAY, "Upstream service rejected request");
    }

    @Bean
    Capability unavailableAsApiException() {
        return new UnavailableAsApiException();
    }

    /**
     * Mất kết nối / timeout / body không đọc được → 503, như ServiceHttpClient cũ.
     * Phải là class public: Feign gọi các hàm enrich bằng reflection.
     */
    public static class UnavailableAsApiException implements Capability {

        @Override
        public InvocationHandlerFactory enrich(InvocationHandlerFactory factory) {
            return (target, dispatch) -> {
                InvocationHandler handler = factory.create(target, dispatch);
                return (proxy, method, args) -> {
                    try {
                        return handler.invoke(proxy, method, args);
                    } catch (ApiException ex) {
                        throw ex;
                    } catch (FeignException ex) {
                        // RetryableException (kết nối / timeout), DecodeException (body lỗi)...
                        throw unavailable();
                    }
                };
            };
        }
    }

    private static ApiException unavailable() {
        return new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Upstream service unavailable");
    }
}
