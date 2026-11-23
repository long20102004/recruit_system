package recruit.demo.dto;

import jakarta.validation.constraints.NotBlank;
import recruit.demo.entity.JobStatus;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

public final class JobDtos {

    private JobDtos() {
    }

    public record JobSkillItem(String name, boolean required) {
    }

    public record JobResponse(
            Integer id,
            String title,
            String company,
            Integer companyId,
            String location,
            String city,
            String workType,
            String level,
            String salaryText,
            BigDecimal minYears,
            JobStatus status,
            boolean hot,
            String description,
            String requirements,
            String responsibilities,
            LocalDateTime postedAt,
            List<String> requiredSkills,
            List<String> preferredSkills
    ) {
    }

    public record CreateJobRequest(
            @NotBlank String title,
            String description,
            String location,
            String city,
            String workType,
            String level,
            String salaryText,
            BigDecimal minYears,
            Boolean hot,
            JobStatus status,
            List<String> requiredSkills,
            List<String> preferredSkills
    ) {
    }

    public record UpdateJobStatusRequest(@NotBlank String status) {
    }
}
