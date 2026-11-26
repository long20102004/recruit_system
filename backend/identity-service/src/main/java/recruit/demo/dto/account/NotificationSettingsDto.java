package recruit.demo.dto.account;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/** Đủ mọi loại thông báo (GET) hoặc các loại cần đổi (PUT). */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NotificationSettingsDto {
    @NotNull @Size(max = 20)
    private List<@Valid @NotNull NotificationPreferenceDto> items;
}
