package recruit.demo.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import recruit.demo.enums.Role;

public final class AuthDtos {

    private AuthDtos() {
    }

    public record LoginRequest(
            @NotBlank @Email String email,
            @NotBlank String password
    ) {
    }

    /** Mật khẩu 8–100 ký tự, có ít nhất một chữ cái và một chữ số. */
    public static final String PASSWORD_PATTERN = "^(?=.*[A-Za-z])(?=.*\\d).{8,100}$";
    public static final String PASSWORD_MESSAGE = "Mật khẩu cần 8–100 ký tự, gồm cả chữ và số";

    public record RegisterRequest(
            @NotBlank @Email String email,
            @NotBlank @Pattern(regexp = PASSWORD_PATTERN, message = PASSWORD_MESSAGE) String password
    ) {
    }

    /** Đăng ký xong chưa đăng nhập: người dùng phải bấm link trong email. */
    public record RegisterResponse(String email, String message) {
    }

    public record TokenRequest(@NotBlank @Size(max = 200) String token) {
    }

    public record EmailRequest(@NotBlank @Email String email) {
    }

    public record ResetPasswordRequest(
            @NotBlank @Size(max = 200) String token,
            @NotBlank @Pattern(regexp = PASSWORD_PATTERN, message = PASSWORD_MESSAGE) String newPassword
    ) {
    }

    public record MessageResponse(String message) {
    }

    public record ChooseRoleRequest(
            @NotNull Role role
    ) {
    }

    /** permissions: quyền của user theo ma trận RBAC (specs/004-rbac), FE dùng để chặn route / ẩn nút. */
    public record UserResponse(
            Integer id,
            String fullName,
            String email,
            Role role,
            boolean roleChosen,
            java.util.List<String> permissions
    ) {
    }

    public record AuthResponse(
            String token,
            UserResponse user
    ) {
    }
}
