package recruit.demo.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;

import java.time.LocalDateTime;

/** DTO cho API quản trị người dùng (/api/admin/users). */
public final class AdminUserDtos {

    private AdminUserDtos() {
    }

    public record AdminUserDto(Integer id, String fullName, String email, Role role, UserStatus status,
                               boolean emailVerified, String lockedReason, LocalDateTime lockedAt,
                               LocalDateTime createdAt) {
    }

    public record LockRequest(@NotBlank @Size(max = 500) String reason) {
    }
}
