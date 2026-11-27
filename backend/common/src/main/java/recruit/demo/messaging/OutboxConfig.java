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

/**
 * Kích hoạt OutboxWriter, OutboxRelay và khai báo topology khi {@code app.outbox.enabled=true}.
 * <p>
 * Không dùng class {@code @Configuration} lồng bên trong: component scan sẽ nhặt class lồng như cấu hình
 * độc lập, bỏ qua điều kiện của class ngoài, làm service không có spring-amqp (identity, interview)
 * lỗi {@code ClassNotFoundException: RabbitTemplate} và notification-service chạy relay không có bảng outbox.
 * Điều kiện ở mức class được đọc từ bytecode (ASM) trước khi nạp class nên an toàn khi thiếu thư viện.
 */
@Configuration(proxyBeanMethods = false)
@ConditionalOnProperty(prefix = "app.outbox", name = "enabled", havingValue = "true")
@ConditionalOnClass(name = {
        "org.springframework.amqp.rabbit.core.RabbitTemplate",
        "org.springframework.jdbc.core.JdbcTemplate"
})
public class OutboxConfig {

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
