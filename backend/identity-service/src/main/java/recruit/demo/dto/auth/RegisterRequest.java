package recruit.demo.dto.auth;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RegisterRequest {
    @NotBlank @Email
    private String email;
    @NotBlank @Pattern(regexp = PasswordPolicy.PATTERN, message = PasswordPolicy.MESSAGE)
    private String password;
}
