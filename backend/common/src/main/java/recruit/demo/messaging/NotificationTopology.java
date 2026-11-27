package recruit.demo.messaging;

import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Declarables;
import org.springframework.amqp.core.FanoutExchange;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.amqp.core.TopicExchange;

/**
 * Topology RabbitMQ của hệ thống thông báo. Khai báo ở cả service phát (outbox) lẫn notification-service
 * để sự kiện không bị RabbitMQ bỏ khi notification-service chưa từng khởi động. Tham số queue phải giống hệt
 * ở mọi nơi khai báo, nên chỉ định nghĩa tại đây.
 */
public final class NotificationTopology {

    private NotificationTopology() {}

    public static Declarables declarables() {
        TopicExchange events = new TopicExchange(NotificationConstants.EXCHANGE, true, false);
        FanoutExchange dlx = new FanoutExchange(NotificationConstants.DLX, true, false);
        Queue queue = QueueBuilder.durable(NotificationConstants.QUEUE)
                .withArgument("x-dead-letter-exchange", NotificationConstants.DLX)
                .build();
        Queue dlq = QueueBuilder.durable(NotificationConstants.DLQ).build();
        return new Declarables(
                events, dlx, queue, dlq,
                BindingBuilder.bind(queue).to(events).with("application.*"),
                BindingBuilder.bind(queue).to(events).with("cv.*"),
                BindingBuilder.bind(queue).to(events).with("company.*"),
                BindingBuilder.bind(queue).to(events).with("job.*"),
                BindingBuilder.bind(dlq).to(dlx));
    }
}
