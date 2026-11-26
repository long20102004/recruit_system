package recruit.demo.controller;

import recruit.demo.dto.admin.MatrixResponse;
import recruit.demo.dto.admin.RoleDto;
import recruit.demo.dto.admin.UpdateRolePermissionsRequest;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import recruit.demo.dto.BaseResponse;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import recruit.demo.service.RbacService;

/** Quản trị ma trận phân quyền (specs/004-rbac). */
@RestController
@RequestMapping("/api/admin/roles")
@RequiredArgsConstructor
@PreAuthorize("hasAuthority('role:manage')")
public class AdminRoleController {

    private final RbacService rbacService;

    @GetMapping
    public BaseResponse<MatrixResponse> matrix() {
        return BaseResponse.success(rbacService.matrix());
    }

    @PutMapping("/{code}/permissions")
    public BaseResponse<RoleDto> update(@PathVariable String code,
                                   @Valid @RequestBody UpdateRolePermissionsRequest request) {
        return BaseResponse.success(rbacService.updateRolePermissions(code, request.getPermissions()));
    }
}
