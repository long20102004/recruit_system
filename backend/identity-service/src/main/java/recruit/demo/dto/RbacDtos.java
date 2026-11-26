package recruit.demo.dto;

import jakarta.validation.constraints.NotNull;

import java.util.List;

/** DTO cho API quản trị phân quyền (/api/admin/roles, specs/004-rbac). */
public final class RbacDtos {

    private RbacDtos() {
    }

    public record PermissionDto(String code, String resource, String description) {
    }

    public record RoleDto(String code, String name, String description, List<String> permissions) {
    }

    /** Ma trận Role → Permission và danh mục permission. */
    public record MatrixResponse(List<RoleDto> roles, List<PermissionDto> permissions) {
    }

    public record UpdateRolePermissionsRequest(@NotNull List<String> permissions) {
    }
}
