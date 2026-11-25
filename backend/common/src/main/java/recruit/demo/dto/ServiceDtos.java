package recruit.demo.dto;
import recruit.demo.entity.Role;
import recruit.demo.entity.UserStatus;
public final class ServiceDtos {
    private ServiceDtos() {}
    /** sessionsValidAfter: epoch giây; JWT có iat nhỏ hơn bị từ chối. Null = không giới hạn. */
    public record UserSnapshot(Integer id, String fullName, String email, String phone, Role role, UserStatus status,
                               Long sessionsValidAfter) {
        public UserSnapshot(Integer id, String fullName, String email, String phone, Role role, UserStatus status) {
            this(id, fullName, email, phone, role, status, null);
        }
    }
    public record ProfileUpdate(String fullName, String phone) {}
    public record InterviewContext(Integer candidateId, Integer userId, Integer jobId, String jobTitle, Integer applicationId,
        java.util.List<String> requiredSkills, java.util.List<String> candidateSkills,
        String seniority, Integer recruiterUserId) {}
    public record QuestionCount(long count) {}
}
