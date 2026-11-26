package recruit.demo.dto.admin;

import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/** Người dùng trong API quản trị (/api/admin/users). */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AdminUserDto {
    private Integer id;
    private String fullName;
    private String email;
    private Role role;
    private UserStatus status;
    private boolean emailVerified;
    private String lockedReason;
    private LocalDateTime lockedAt;
    private LocalDateTime createdAt;
}
