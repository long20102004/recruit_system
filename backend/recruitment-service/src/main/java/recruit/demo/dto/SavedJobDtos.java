package recruit.demo.dto;

import java.time.LocalDateTime;
import java.util.List;

public final class SavedJobDtos {

    private SavedJobDtos() {
    }

    public record SavedJobResponse(
            Integer id,
            Integer jobId,
            String title,
            String company,
            String logo,
            String city,
            String mode,
            String level,
            String salary,
            List<String> skills,
            LocalDateTime savedAt,
            LocalDateTime deadline,
            String status,
            boolean hot,
            Integer match
    ) {
    }
}
