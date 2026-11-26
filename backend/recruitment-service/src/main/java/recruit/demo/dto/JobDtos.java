package recruit.demo.dto;

import jakarta.validation.constraints.NotBlank;
import recruit.demo.enums.JobStatus;

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
            List<String> preferredSkills,
            /** Yeu cau ung vien, moi dong mot y (ghep ho so dung cho feature B5 / hien thi). */
            String requirements,
            /** Trach nhiem cong viec, moi dong mot y (feature B4 cua cvmatch). */
            String responsibilities
    ) {
        public CreateJobRequest(String title, String description, String location, String city, String workType,
                                String level, String salaryText, BigDecimal minYears, Boolean hot, JobStatus status,
                                List<String> requiredSkills, List<String> preferredSkills) {
            this(title, description, location, city, workType, level, salaryText, minYears, hot, status,
                    requiredSkills, preferredSkills, null, null);
        }
    }

    public record UpdateJobStatusRequest(@NotBlank String status) {
    }
}
