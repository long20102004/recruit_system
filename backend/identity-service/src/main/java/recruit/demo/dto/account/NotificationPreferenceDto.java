package recruit.demo.dto.account;

import jakarta.validation.constraints.NotNull;
import recruit.demo.enums.NotificationType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/** Bật/tắt một loại thông báo trong ứng dụng và qua email. */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NotificationPreferenceDto {
    @NotNull
    private NotificationType type;
    private boolean inApp;
    private boolean email;
}
