package recruit.demo.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "app")
public class AppProperties {

    private final Jwt jwt = new Jwt();
    private final Cors cors = new Cors();
    private final Upload upload = new Upload();
    private final Ai ai = new Ai();

    @Getter
    @Setter
    public static class Jwt {
        private String secret;
        private long expirationMs;
    }

    @Getter
    @Setter
    public static class Cors {
        private String allowedOrigins;
    }

    @Getter
    @Setter
    public static class Upload {
        private String path;
    }

    @Getter
    @Setter
    public static class Ai {
        /** FastAPI scoring service base URL */
        private String baseUrl = "http://localhost:8000";
        private boolean enabled = true;
        /** fast | bertscore | finetune */
        private String mode = "fast";
        private int connectTimeoutMs = 3000;
        private int readTimeoutMs = 60000;
        /** If AI is down, fall back to keyword rubric scoring (default off — require AI) */
        private boolean fallbackToRule = false;
    }
}
