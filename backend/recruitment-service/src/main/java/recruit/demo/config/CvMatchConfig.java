package recruit.demo.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

/** Chay nen dong bo cvmatch (listener @Async) va thu lai dinh ky (@Scheduled). */
@Configuration
@EnableAsync
@EnableScheduling
public class CvMatchConfig {
}
