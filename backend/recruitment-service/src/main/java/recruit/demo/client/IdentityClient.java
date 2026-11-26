package recruit.demo.client;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import recruit.demo.dto.ServiceDtos.*;
@Slf4j
@Component
public class IdentityClient {
    private final IdentityServiceClient identity;
    public IdentityClient(IdentityServiceClient identity) {
        this.identity = identity;
    }
    public UserSnapshot get(Integer id) { return identity.getUser(id); }
    public void update(Integer id, String name, String phone) {
        identity.updateUser(id, new ProfileUpdate(name, phone));
    }
    public void recordAuditLog(String eventType, String eventLabel, String badgeClass,
                               String target, Integer actorUserId, String actorEmail) {
        try {
            identity.recordAuditLog(new AuditLogCreateRequest(
                    eventType, eventLabel, badgeClass, target, actorUserId,
                    actorEmail != null ? actorEmail : "system@hirelens.local"));
        } catch (Exception ex) {
            log.warn("Audit log skipped ({}): {}", eventType, ex.getMessage());
        }
    }
}
