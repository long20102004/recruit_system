package recruit.demo.client;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import recruit.demo.dto.ServiceDtos.*;
@Component
public class IdentityClient {
    private final ServiceHttpClient http;
    private final String url;
    public IdentityClient(ServiceHttpClient http, @Value("${app.services.identity-url}") String url) {
        this.http = http; this.url = url;
    }
    public UserSnapshot get(Integer id) { return http.get(url + "/internal/users/" + id, UserSnapshot.class); }
    public void update(Integer id, String name, String phone) {
        http.patch(url + "/internal/users/" + id, new ProfileUpdate(name, phone), UserSnapshot.class);
    }
}
