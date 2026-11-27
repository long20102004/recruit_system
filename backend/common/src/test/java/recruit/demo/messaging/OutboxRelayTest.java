package recruit.demo.messaging;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.transaction.TransactionStatus;
import org.springframework.transaction.support.TransactionTemplate;
import recruit.demo.enums.NotificationType;
import tools.jackson.databind.ObjectMapper;

import java.sql.Timestamp;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class OutboxRelayTest {

    @Test
    void outboxWriterSerializesEventAndGeneratesEventId() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        ObjectMapper mapper = new ObjectMapper();
        OutboxWriter writer = new OutboxWriter(jdbc, mapper);

        NotificationEvent event = NotificationEvent.builder()
                .type(NotificationType.APPLICATION_STATUS)
                .recipientUserIds(List.of(70))
                .title("Đơn đã được xem xét")
                .body("Backend Engineer")
                .link("/candidate/applications/12")
                .data(Map.of("applicationId", 12))
                .build();

        String eventId = writer.add(NotificationConstants.RK_APPLICATION_STATUS_CHANGED, event);

        assertNotNull(eventId);
        ArgumentCaptor<String> payloadCap = ArgumentCaptor.forClass(String.class);
        verify(jdbc).update(contains("INSERT INTO outbox_events"), eq(eventId),
                eq(NotificationConstants.RK_APPLICATION_STATUS_CHANGED), payloadCap.capture(), any(Timestamp.class));
        assertTrue(payloadCap.getValue().contains("\"APPLICATION_STATUS\""));
        assertTrue(payloadCap.getValue().contains("\"recipientUserIds\":[70]"));
    }

    @Test
    void outboxRelayMarksPublishedOnBrokerAck() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        RabbitTemplate rabbit = mock(RabbitTemplate.class);
        TransactionTemplate tx = mock(TransactionTemplate.class);
        doAnswer(inv -> {
            Consumer<TransactionStatus> cb = inv.getArgument(0);
            cb.accept(mock(TransactionStatus.class));
            return null;
        }).when(tx).executeWithoutResult(any());

        OutboxEvent pending = OutboxEvent.builder()
                .id(1L).eventId("evt-1").routingKey("application.status-changed").payload("{\"eventId\":\"evt-1\"}")
                .build();
        when(jdbc.query(anyString(), any(RowMapper.class))).thenReturn(List.of(pending));
        doAnswer(inv -> {
            CorrelationData cd = inv.getArgument(3);
            cd.getFuture().complete(new CorrelationData.Confirm(true, null));
            return null;
        }).when(rabbit).send(eq(NotificationConstants.EXCHANGE), eq("application.status-changed"), any(Message.class), any(CorrelationData.class));

        new OutboxRelay(jdbc, rabbit, tx).relayBatch();

        verify(jdbc).update(contains("SET published_at = ?"), any(Timestamp.class), eq(1L));
    }

    @Test
    void outboxRelayIncrementsAttemptsOnBrokerFailure() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        RabbitTemplate rabbit = mock(RabbitTemplate.class);
        TransactionTemplate tx = mock(TransactionTemplate.class);
        doAnswer(inv -> {
            Consumer<TransactionStatus> cb = inv.getArgument(0);
            cb.accept(mock(TransactionStatus.class));
            return null;
        }).when(tx).executeWithoutResult(any());

        OutboxEvent pending = OutboxEvent.builder()
                .id(2L).eventId("evt-2").routingKey("cv.processed").payload("{}")
                .build();
        when(jdbc.query(anyString(), any(RowMapper.class))).thenReturn(List.of(pending));
        doThrow(new RuntimeException("RabbitMQ down"))
                .when(rabbit).send(anyString(), anyString(), any(Message.class), any(CorrelationData.class));

        new OutboxRelay(jdbc, rabbit, tx).relayBatch();

        verify(jdbc).update(contains("SET attempts = attempts + 1"), contains("RabbitMQ down"), eq(2L));
    }

    private static TransactionTemplate inlineTx() {
        TransactionTemplate tx = mock(TransactionTemplate.class);
        doAnswer(inv -> {
            Consumer<TransactionStatus> cb = inv.getArgument(0);
            cb.accept(mock(TransactionStatus.class));
            return null;
        }).when(tx).executeWithoutResult(any());
        return tx;
    }

    @Test
    void unroutableMessageIsNotMarkedPublishedAndStopsBatch() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        RabbitTemplate rabbit = mock(RabbitTemplate.class);
        OutboxEvent first = OutboxEvent.builder().id(3L).eventId("evt-3").routingKey("job.locked").payload("{}").build();
        OutboxEvent second = OutboxEvent.builder().id(4L).eventId("evt-4").routingKey("job.locked").payload("{}").build();
        when(jdbc.query(anyString(), any(RowMapper.class))).thenReturn(List.of(first, second));
        doAnswer(inv -> {
            CorrelationData cd = inv.getArgument(3);
            // mandatory: broker trả message về rồi vẫn ack
            cd.setReturned(new org.springframework.amqp.core.ReturnedMessage(
                    inv.getArgument(2), 312, "NO_ROUTE", NotificationConstants.EXCHANGE, "job.locked"));
            cd.getFuture().complete(new CorrelationData.Confirm(true, null));
            return null;
        }).when(rabbit).send(anyString(), anyString(), any(Message.class), any(CorrelationData.class));

        new OutboxRelay(jdbc, rabbit, inlineTx()).relayBatch();

        verify(jdbc, never()).update(contains("SET published_at = ?"), any(), any());
        verify(jdbc).update(contains("SET attempts = attempts + 1"), contains("NO_ROUTE"), eq(3L));
        verify(rabbit, times(1)).send(anyString(), anyString(), any(Message.class), any(CorrelationData.class));
    }

    @Test
    void topologyDeclaresQueueWithDeadLetterAndBindings() {
        var declarables = NotificationTopology.declarables().getDeclarables();
        var queue = declarables.stream()
                .filter(d -> d instanceof org.springframework.amqp.core.Queue q && q.getName().equals(NotificationConstants.QUEUE))
                .map(d -> (org.springframework.amqp.core.Queue) d).findFirst().orElseThrow();
        assertEquals(NotificationConstants.DLX, queue.getArguments().get("x-dead-letter-exchange"));
        assertEquals(5, declarables.stream().filter(d -> d instanceof org.springframework.amqp.core.Binding).count());
    }
}
