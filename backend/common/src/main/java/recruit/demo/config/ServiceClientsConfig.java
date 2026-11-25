package recruit.demo.config;

import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.context.annotation.Configuration;
import recruit.demo.client.ServiceClientConfiguration;

/** Bật Feign client gọi giữa các service (package recruit.demo.client) với cấu hình chung. */
@Configuration
@EnableFeignClients(basePackages = "recruit.demo.client", defaultConfiguration = ServiceClientConfiguration.class)
public class ServiceClientsConfig {
}
