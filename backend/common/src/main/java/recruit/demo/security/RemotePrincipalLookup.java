package recruit.demo.security;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import recruit.demo.client.ServiceHttpClient;
import recruit.demo.dto.ServiceDtos.UserSnapshot;
import recruit.demo.exception.ApiException;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
@Component
@ConditionalOnProperty(name="app.identity.remote", havingValue="true")
public class RemotePrincipalLookup implements PrincipalLookup {
    private final ServiceHttpClient http;
    private final String identityUrl;
    private final UserSnapshotCache cache;
    public RemotePrincipalLookup(ServiceHttpClient http, @Value("${app.services.identity-url}") String url,
                                 UserSnapshotCache cache) {
        this.http = http; identityUrl = url; this.cache = cache;
    }
    public UserPrincipal load(Integer id, String email) {
        UserSnapshot user = cache.get(id).orElse(null);
        if (user == null) {
            try { user = http.get(identityUrl + "/internal/users/" + id, UserSnapshot.class); }
            catch (ApiException ex) {
                if (ex.getStatus().value() == 404) throw new UsernameNotFoundException("User not found");
                throw ex;
            }
            cache.put(user);
        }
        if (!user.email().equalsIgnoreCase(email)) throw new UsernameNotFoundException("User not found");
        return new UserPrincipal(user.id(), user.email(), "", user.fullName(), user.role(), user.status(),
                user.sessionsValidAfter());
    }
}
