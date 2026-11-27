package recruit.demo.storage;

import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;

import static org.assertj.core.api.Assertions.assertThat;

/** FR-007: thiếu cấu hình R2 thì context không khởi động được. */
class R2PropertiesValidationTest {

    @Configuration
    @EnableConfigurationProperties(R2Properties.class)
    static class Cfg {
    }

    private final ApplicationContextRunner runner = new ApplicationContextRunner().withUserConfiguration(Cfg.class);

    @Test
    void failsFastWhenRequiredValuesMissing() {
        runner.withPropertyValues("storage.r2.account-id=acc")
                .run(ctx -> assertThat(ctx).hasFailed());
    }

    @Test
    void startsWithCompleteConfig() {
        runner.withPropertyValues(
                        "storage.r2.account-id=acc",
                        "storage.r2.access-key-id=k",
                        "storage.r2.secret-access-key=s",
                        "storage.r2.private-bucket=p",
                        "storage.r2.public-bucket=q",
                        "storage.r2.public-base-url=https://pub.test",
                        "storage.r2.presign-ttl=2m")
                .run(ctx -> {
                    assertThat(ctx).hasNotFailed();
                    assertThat(ctx.getBean(R2Properties.class).getPresignTtl().toMinutes()).isEqualTo(2);
                });
    }
}
