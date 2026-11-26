package recruit.demo.dto;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
public final class ServiceDtos {
    private ServiceDtos() {}
    /** sessionsValidAfter: epoch giây; JWT có iat nhỏ hơn bị từ chối. Null = không giới hạn. */
    /** permissions: quyền theo ma trận RBAC của role (specs/004-rbac); null/rỗng = không có quyền nghiệp vụ nào. */
    public record UserSnapshot(Integer id, String fullName, String email, String phone, Role role, UserStatus status,
                               Long sessionsValidAfter, java.util.List<String> permissions) {
        public UserSnapshot(Integer id, String fullName, String email, String phone, Role role, UserStatus status) {
            this(id, fullName, email, phone, role, status, null, java.util.List.of());
        }
        public UserSnapshot(Integer id, String fullName, String email, String phone, Role role, UserStatus status,
                            Long sessionsValidAfter) {
            this(id, fullName, email, phone, role, status, sessionsValidAfter, java.util.List.of());
        }
    }
    public record ProfileUpdate(String fullName, String phone) {}
    public record InterviewContext(Integer candidateId, Integer userId, Integer jobId, String jobTitle, Integer applicationId,
        java.util.List<String> requiredSkills, java.util.List<String> candidateSkills,
        String seniority, Integer recruiterUserId) {}
    public record QuestionCount(long count) {}
}
