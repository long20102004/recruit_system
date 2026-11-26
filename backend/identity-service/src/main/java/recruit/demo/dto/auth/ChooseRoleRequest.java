package recruit.demo.dto.auth;

import jakarta.validation.constraints.NotNull;
import recruit.demo.enums.Role;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChooseRoleRequest {
    @NotNull
    private Role role;
}
