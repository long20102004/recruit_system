package recruit.demo.config;

import org.springframework.amqp.core.Declarables;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import recruit.demo.messaging.NotificationTopology;

@Configuration
public class RabbitTopologyConfig {

    /** Topology dùng chung với service phát sự kiện (recruit.demo.messaging.NotificationTopology). */
    @Bean
    public Declarables notificationRabbitTopology() {
        return NotificationTopology.declarables();
    }
}
