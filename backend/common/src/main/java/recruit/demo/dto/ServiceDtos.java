package recruit.demo.dto;
import recruit.demo.entity.Role;
import recruit.demo.entity.UserStatus;
public final class ServiceDtos {
    private ServiceDtos() {}
    public record UserSnapshot(Integer id, String fullName, String email, String phone, Role role, UserStatus status) {}
    public record ProfileUpdate(String fullName, String phone) {}
    public record InterviewContext(Integer candidateId, Integer userId, Integer jobId, String jobTitle, Integer applicationId,
        java.util.List<String> requiredSkills, java.util.List<String> candidateSkills,
        String seniority, Integer recruiterUserId) {}
    public record QuestionCount(long count) {}
}
