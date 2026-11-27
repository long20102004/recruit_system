package recruit.demo.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import recruit.demo.entity.NotificationEntity;
import recruit.demo.enums.NotificationType;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NotificationDto {
    private Long id;
    private NotificationType type;
    private String category;
    private String title;
    private String body;
    private String link;
    private boolean read;
    private Instant createdAt;

    public static NotificationDto from(NotificationEntity entity) {
        return NotificationDto.builder()
                .id(entity.getId())
                .type(entity.getType())
                .category(entity.getCategory())
                .title(entity.getTitle())
                .body(entity.getBody())
                .link(entity.getLink())
                .read(entity.getReadAt() != null)
                .createdAt(entity.getCreatedAt())
                .build();
    }
}
