package recruit.demo.dto.auth;

import recruit.demo.enums.Role;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/** permissions: quyền của user theo ma trận RBAC (specs/004-rbac), FE dùng để chặn route / ẩn nút. */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserResponse {
    private Integer id;
    private String fullName;
    private String email;
    private Role role;
    private boolean roleChosen;
    private List<String> permissions;
}
