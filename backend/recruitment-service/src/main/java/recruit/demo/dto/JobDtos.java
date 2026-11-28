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
            List<String> preferredSkills,
            BigDecimal salaryMin,
            BigDecimal salaryMax,
            String currency,
            Integer headcount,
            String benefits,
            LocalDateTime deadline,
            Integer defaultInterviewQuestions,
            String lockReason,
            String lockNote,
            LocalDateTime lockedAt,
            long applicantsCount,
            Integer createdById
    ) {
        public JobResponse(
                Integer id, String title, String company, Integer companyId, String location, String city,
                String workType, String level, String salaryText, BigDecimal minYears, JobStatus status,
                boolean hot, String description, String requirements, String responsibilities,
                LocalDateTime postedAt, List<String> requiredSkills, List<String> preferredSkills) {
            this(id, title, company, companyId, location, city, workType, level, salaryText, minYears, status,
                    hot, description, requirements, responsibilities, postedAt, requiredSkills, preferredSkills,
                    null, null, "VND", null, null, null, 5, null, null, null, 0L, null);
        }
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
            String requirements,
            String responsibilities,
            BigDecimal salaryMin,
            BigDecimal salaryMax,
            String currency,
            Integer headcount,
            String benefits,
            LocalDateTime deadline,
            Integer defaultInterviewQuestions
    ) {
        public CreateJobRequest(String title, String description, String location, String city, String workType,
                                String level, String salaryText, BigDecimal minYears, Boolean hot, JobStatus status,
                                List<String> requiredSkills, List<String> preferredSkills) {
            this(title, description, location, city, workType, level, salaryText, minYears, hot, status,
                    requiredSkills, preferredSkills, null, null, null, null, null, null, null, null, null);
        }

        public CreateJobRequest(String title, String description, String location, String city, String workType,
                                String level, String salaryText, BigDecimal minYears, Boolean hot, JobStatus status,
                                List<String> requiredSkills, List<String> preferredSkills,
                                String requirements, String responsibilities) {
            this(title, description, location, city, workType, level, salaryText, minYears, hot, status,
                    requiredSkills, preferredSkills, requirements, responsibilities, null, null, null, null, null, null, null);
        }
    }

    public record UpdateJobRequest(
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
            String requirements,
            String responsibilities,
            BigDecimal salaryMin,
            BigDecimal salaryMax,
            String currency,
            Integer headcount,
            String benefits,
            LocalDateTime deadline,
            Integer defaultInterviewQuestions
    ) {
    }

    public record UpdateJobStatusRequest(@NotBlank String status) {
    }

    public record RenewJobRequest(LocalDateTime deadline) {
    }

    public record AdminLockJobRequest(@NotBlank String reason, String note) {
    }

    public record JobLockStateDto(
            Integer jobId,
            boolean locked,
            String reason,
            String note,
            LocalDateTime lockedAt
    ) {
    }

    public record ModeratedJob(JobResponse job, LocalDateTime lockedAt, String reason, String note) {
    }

    public record LockRequest(
            @NotBlank @jakarta.validation.constraints.Size(max = 255) String reason,
            @jakarta.validation.constraints.Size(max = 1000) String note
    ) {
    }
}
