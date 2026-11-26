package recruit.demo.entity;

import jakarta.persistence.*;
import lombok.*;
import recruit.demo.enums.NotificationType;

import java.io.Serializable;

@Entity
@Table(name = "notification_preferences")
@IdClass(NotificationPreference.Key.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class NotificationPreference {

    @Id
    @Column(name = "user_id")
    private Integer userId;

    @Id
    @Enumerated(EnumType.STRING)
    @Column(length = 40)
    private NotificationType type;

    @Column(name = "in_app", nullable = false)
    private boolean inApp;

    @Column(nullable = false)
    private boolean email;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Key implements Serializable {
        private Integer userId;
        private NotificationType type;
    }
}
