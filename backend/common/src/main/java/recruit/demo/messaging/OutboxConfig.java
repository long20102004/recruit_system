package recruit.demo.messaging;

import org.springframework.amqp.core.Declarables;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.ObjectMapper;

/** Kích hoạt OutboxWriter, OutboxRelay và khai báo exchange khi {@code app.outbox.enabled=true}. */
@Configuration(proxyBeanMethods = false)
@ConditionalOnProperty(prefix = "app.outbox", name = "enabled", havingValue = "true")
@ConditionalOnClass(name = {
        "org.springframework.amqp.rabbit.core.RabbitTemplate",
        "org.springframework.jdbc.core.JdbcTemplate"
})
public class OutboxConfig {

    @Configuration(proxyBeanMethods = false)
    static class AmqpOutboxBeans {

        @Bean
        Declarables hirelensNotificationTopology() {
            return NotificationTopology.declarables();
        }

        @Bean
        OutboxWriter outboxWriter(JdbcTemplate jdbcTemplate, ObjectMapper objectMapper) {
            return new OutboxWriter(jdbcTemplate, objectMapper);
        }

        @Bean
        OutboxRelay outboxRelay(JdbcTemplate jdbcTemplate, RabbitTemplate rabbitTemplate,
                                TransactionTemplate transactionTemplate) {
            return new OutboxRelay(jdbcTemplate, rabbitTemplate, transactionTemplate);
        }
    }
}
