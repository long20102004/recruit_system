package recruit.demo.messaging;

import org.junit.jupiter.api.Test;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.boot.test.context.FilteredClassLoader;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.ObjectMapper;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

/**
 * OutboxConfig được nhặt qua component scan ở mọi service dùng common. Phải:
 * - không lỗi khi thiếu spring-amqp (identity, interview);
 * - không tạo relay khi chưa bật app.outbox.enabled (notification-service không có bảng outbox).
 */
class OutboxConfigScanTest {

    @Configuration(proxyBeanMethods = false)
    @ComponentScan(basePackageClasses = OutboxConfig.class)
    static class ScanMessaging {
    }

    @Configuration(proxyBeanMethods = false)
    static class Infra {
        @Bean JdbcTemplate jdbcTemplate() { return mock(JdbcTemplate.class); }
        @Bean RabbitTemplate rabbitTemplate() { return mock(RabbitTemplate.class); }
        @Bean TransactionTemplate transactionTemplate() { return mock(TransactionTemplate.class); }
        @Bean ObjectMapper objectMapper() { return new ObjectMapper(); }
    }

    private final ApplicationContextRunner runner =
            new ApplicationContextRunner().withUserConfiguration(ScanMessaging.class, Infra.class);

    @Test
    void scanWithoutAmqpOnClasspathStartsAndSkipsOutbox() {
        new ApplicationContextRunner()
                .withClassLoader(new FilteredClassLoader(RabbitTemplate.class))
                .withUserConfiguration(ScanMessaging.class)
                .withPropertyValues("app.outbox.enabled=true")
                .run(ctx -> {
                    assertThat(ctx).hasNotFailed();
                    assertThat(ctx).doesNotHaveBean(OutboxRelay.class);
                });
    }

    @Test
    void outboxDisabledByDefaultEvenWithAmqp() {
        runner.run(ctx -> {
            assertThat(ctx).hasNotFailed();
            assertThat(ctx).doesNotHaveBean(OutboxRelay.class);
            assertThat(ctx).doesNotHaveBean(OutboxWriter.class);
        });
    }

    @Test
    void outboxEnabledCreatesWriterRelayAndTopology() {
        runner.withPropertyValues("app.outbox.enabled=true").run(ctx -> {
            assertThat(ctx).hasNotFailed();
            assertThat(ctx).hasSingleBean(OutboxRelay.class);
            assertThat(ctx).hasSingleBean(OutboxWriter.class);
            assertThat(ctx).hasBean("hirelensNotificationTopology");
        });
    }
}
