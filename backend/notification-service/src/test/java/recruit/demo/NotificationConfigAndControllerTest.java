package recruit.demo;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.core.AcknowledgeMode;
import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.Declarables;
import org.springframework.amqp.core.Queue;
import org.springframework.boot.amqp.autoconfigure.RabbitProperties;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.boot.env.YamlPropertySourceLoader;
import org.springframework.core.env.MutablePropertySources;
import org.springframework.core.env.PropertySource;
import org.springframework.core.env.StandardEnvironment;
import org.springframework.core.io.ClassPathResource;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import recruit.demo.config.NotificationProperties;
import recruit.demo.config.RabbitTopologyConfig;
import recruit.demo.controller.NotificationController;
import recruit.demo.dto.UnreadCountDto;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
import recruit.demo.messaging.NotificationConstants;
import recruit.demo.security.UserPrincipal;
import recruit.demo.service.NotificationService;
import recruit.demo.service.SseHub;

import java.io.IOException;
import java.time.Duration;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class NotificationConfigAndControllerTest {

    @AfterEach
    void clearSecurity() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void applicationYmlBindsRabbitAndNotificationProperties() throws IOException {
        List<PropertySource<?>> loaded = new YamlPropertySourceLoader()
                .load("application", new ClassPathResource("application.yml"));
        StandardEnvironment env = new StandardEnvironment();
        MutablePropertySources sources = env.getPropertySources();
        loaded.forEach(sources::addFirst);

        Binder binder = Binder.get(env);
        RabbitProperties rabbit = binder.bind("spring.rabbitmq", RabbitProperties.class).get();
        NotificationProperties notif = binder.bind("app.notification", NotificationProperties.class).get();

        assertEquals(AcknowledgeMode.AUTO, rabbit.getListener().getSimple().getAcknowledgeMode());
        assertEquals(10, rabbit.getListener().getSimple().getPrefetch());
        assertEquals(Boolean.FALSE, rabbit.getListener().getSimple().getDefaultRequeueRejected());
        assertTrue(rabbit.getListener().getSimple().getRetry().isEnabled());
        assertEquals(3L, rabbit.getListener().getSimple().getRetry().getMaxRetries());
        assertEquals(Duration.ofMillis(1000), rabbit.getListener().getSimple().getRetry().getInitialInterval());
        assertEquals(2.0, rabbit.getListener().getSimple().getRetry().getMultiplier());
        assertEquals(Duration.ofMillis(4000), rabbit.getListener().getSimple().getRetry().getMaxInterval());

        assertEquals("HireLens <no-reply@hirelens.local>", notif.getMailFrom());
        assertEquals("http://localhost:5173", notif.getFrontendUrl());
        assertEquals(5000L, notif.getEmailPollMs());
    }

    @Test
    void rabbitTopologyDeclaresExchangesQueuesAndBindings() {
        Declarables declarables = new RabbitTopologyConfig().notificationRabbitTopology();
        List<Queue> queues = declarables.getDeclarablesByType(Queue.class);
        List<Binding> bindings = declarables.getDeclarablesByType(Binding.class);

        Queue mainQueue = queues.stream()
                .filter(q -> NotificationConstants.QUEUE.equals(q.getName()))
                .findFirst()
                .orElseThrow();
        assertEquals(NotificationConstants.DLX, mainQueue.getArguments().get("x-dead-letter-exchange"));
        assertTrue(queues.stream().anyMatch(q -> NotificationConstants.DLQ.equals(q.getName())));
        assertEquals(5, bindings.size());
    }

    @Test
    void controllerUsesCurrentUserAndDelegatesStream() {
        NotificationService service = mock(NotificationService.class);
        SseHub sseHub = new SseHub();
        NotificationController controller = new NotificationController(service, sseHub);

        UserPrincipal principal = new UserPrincipal(42, "u@test.local", "", "User", Role.CANDIDATE, UserStatus.ACTIVE);
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(principal, null, principal.getAuthorities()));

        when(service.unreadCount(42)).thenReturn(new UnreadCountDto(2));

        assertEquals(2L, controller.unreadCount().getData().getCount());
        SseEmitter emitter = controller.stream();
        assertNotNull(emitter);
        verify(service, times(2)).unreadCount(42);
    }
}
