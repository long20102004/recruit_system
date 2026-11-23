package recruit.demo.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import recruit.demo.entity.Role;

public final class AuthDtos {

    private AuthDtos() {
    }

    public record LoginRequest(
            @NotBlank @Email String email,
            @NotBlank String password
    ) {
    }

    public record RegisterRequest(
            @NotBlank @Email String email,
            @NotBlank @Size(min = 6, max = 100) String password
    ) {
    }

    public record ChooseRoleRequest(
            @NotNull Role role
    ) {
    }

    public record UserResponse(
            Integer id,
            String fullName,
            String email,
            Role role,
            boolean roleChosen
    ) {
    }

    public record AuthResponse(
            String token,
            UserResponse user
    ) {
    }
}
