package recruit.demo.service;

import recruit.demo.security.UserPrincipal;

public interface ProfileProvisioningService {
    void ensureProfile(UserPrincipal user);
}
