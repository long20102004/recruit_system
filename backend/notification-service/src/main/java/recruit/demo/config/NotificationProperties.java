package recruit.demo.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Getter
@Setter
@ConfigurationProperties(prefix = "app.notification")
public class NotificationProperties {

    private String mailFrom = "HireLens <no-reply@hirelens.local>";
    private String frontendUrl = "http://localhost:5173";
    private long emailPollMs = 5000L;
}
