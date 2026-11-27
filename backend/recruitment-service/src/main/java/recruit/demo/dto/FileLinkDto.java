package recruit.demo.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/** Link tải file private trên R2, chỉ dùng được tới {@code expiresAt} (specs/008-r2-storage). */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FileLinkDto {
    private String url;
    private Instant expiresAt;
}
