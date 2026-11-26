package recruit.demo.dto.admin;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/** Ma trận Role → Permission và danh mục permission (specs/004-rbac). */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MatrixResponse {
    private List<RoleDto> roles;
    private List<PermissionDto> permissions;
}
