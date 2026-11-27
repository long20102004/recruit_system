package recruit.demo.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import recruit.demo.dto.NotificationDto;
import recruit.demo.dto.UnreadCountDto;

import java.io.IOException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

@Slf4j
@Component
public class SseHub {

    private static final long SSE_TIMEOUT_MS = 30L * 60 * 1000L;

    private final ConcurrentHashMap<Integer, CopyOnWriteArrayList<SseEmitter>> emitters = new ConcurrentHashMap<>();

    public SseEmitter subscribe(Integer userId, long initialUnread) {
        SseEmitter emitter = new SseEmitter(SSE_TIMEOUT_MS);
        emitters.computeIfAbsent(userId, k -> new CopyOnWriteArrayList<>()).add(emitter);

        emitter.onCompletion(() -> removeEmitter(userId, emitter));
        emitter.onTimeout(() -> removeEmitter(userId, emitter));
        emitter.onError(ex -> removeEmitter(userId, emitter));

        try {
            emitter.send(SseEmitter.event()
                    .name("unread")
                    .data(new UnreadCountDto(initialUnread)));
        } catch (IOException | IllegalStateException ex) {
            removeEmitter(userId, emitter);
            emitter.completeWithError(ex);
        }
        return emitter;
    }

    public void pushNotification(Integer userId, NotificationDto dto, long unreadCount) {
        CopyOnWriteArrayList<SseEmitter> list = emitters.get(userId);
        if (list == null || list.isEmpty()) {
            return;
        }
        for (SseEmitter emitter : list) {
            try {
                emitter.send(SseEmitter.event().name("notification").data(dto));
                emitter.send(SseEmitter.event().name("unread").data(new UnreadCountDto(unreadCount)));
            } catch (IOException | IllegalStateException ex) {
                log.debug("Removing broken SSE emitter for userId={}", userId);
                removeEmitter(userId, emitter);
            }
        }
    }

    /** Đẩy số chưa đọc tới mọi tab của user (vd sau khi đánh dấu đã đọc) để chuông đồng bộ. */
    public void pushUnread(Integer userId, long unreadCount) {
        CopyOnWriteArrayList<SseEmitter> list = emitters.get(userId);
        if (list == null || list.isEmpty()) {
            return;
        }
        for (SseEmitter emitter : list) {
            try {
                emitter.send(SseEmitter.event().name("unread").data(new UnreadCountDto(unreadCount)));
            } catch (IOException | IllegalStateException ex) {
                removeEmitter(userId, emitter);
            }
        }
    }

    @Scheduled(fixedRate = 25000)
    public void heartbeat() {
        emitters.forEach((userId, list) -> {
            for (SseEmitter emitter : list) {
                try {
                    emitter.send(SseEmitter.event().name("ping").data("ok"));
                } catch (IOException | IllegalStateException ex) {
                    removeEmitter(userId, emitter);
                }
            }
        });
    }

    private void removeEmitter(Integer userId, SseEmitter emitter) {
        emitters.computeIfPresent(userId, (k, list) -> {
            list.remove(emitter);
            return list.isEmpty() ? null : list;
        });
    }
}
