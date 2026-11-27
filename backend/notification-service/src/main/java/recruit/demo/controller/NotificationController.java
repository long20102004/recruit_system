package recruit.demo.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.NotificationDto;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.UnreadCountDto;
import recruit.demo.security.SecurityUtils;
import recruit.demo.service.NotificationService;
import recruit.demo.service.SseHub;

@RestController
@RequestMapping("/api/notifications")
@RequiredArgsConstructor
public class NotificationController {

    private final NotificationService notificationService;
    private final SseHub sseHub;

    @GetMapping
    public BaseResponse<PageResponse<NotificationDto>> list(
            @RequestParam(required = false) String category,
            @RequestParam(required = false) Boolean unread,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Integer userId = SecurityUtils.currentUser().getId();
        return BaseResponse.success(notificationService.listNotifications(userId, category, unread, page, size));
    }

    @GetMapping("/unread-count")
    public BaseResponse<UnreadCountDto> unreadCount() {
        Integer userId = SecurityUtils.currentUser().getId();
        return BaseResponse.success(notificationService.unreadCount(userId));
    }

    @PostMapping("/{id}/read")
    public BaseResponse<NotificationDto> markRead(@PathVariable Long id) {
        Integer userId = SecurityUtils.currentUser().getId();
        return BaseResponse.success(notificationService.markRead(userId, id));
    }

    @PostMapping("/read-all")
    public BaseResponse<UnreadCountDto> markAllRead() {
        Integer userId = SecurityUtils.currentUser().getId();
        return BaseResponse.success(notificationService.markAllRead(userId));
    }

    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter stream() {
        Integer userId = SecurityUtils.currentUser().getId();
        long unread = notificationService.unreadCount(userId).getCount();
        return sseHub.subscribe(userId, unread);
    }
}
