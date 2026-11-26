package recruit.demo.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import recruit.demo.dto.ServiceDtos.AuditLogCreateRequest;
import recruit.demo.dto.ServiceDtos.ProfileUpdate;
import recruit.demo.dto.ServiceDtos.UserSnapshot;

/** API nội bộ của identity-service (/internal/users). */
@FeignClient(name = "identity-service", contextId = "identityServiceClient", url = "${app.services.identity-url}")
public interface IdentityServiceClient {

    @GetMapping("/internal/users/{id}")
    UserSnapshot getUser(@PathVariable("id") Integer id);

    @PatchMapping("/internal/users/{id}")
    UserSnapshot updateUser(@PathVariable("id") Integer id, @RequestBody ProfileUpdate update);

    @PostMapping("/internal/audit-logs")
    void recordAuditLog(@RequestBody AuditLogCreateRequest request);
}
