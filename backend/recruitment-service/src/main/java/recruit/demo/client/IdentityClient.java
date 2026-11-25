package recruit.demo.client;
import org.springframework.stereotype.Component;
import recruit.demo.dto.ServiceDtos.*;
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
}
