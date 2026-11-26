package recruit.demo.controller;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.RbacDtos;
import recruit.demo.service.RbacService;

/** Quản trị ma trận phân quyền (specs/004-rbac). */
@RestController
@RequestMapping("/api/admin/roles")
@RequiredArgsConstructor
@PreAuthorize("hasAuthority('role:manage')")
public class AdminRoleController {

    private final RbacService rbacService;

    @GetMapping
    public RbacDtos.MatrixResponse matrix() {
        return rbacService.matrix();
    }

    @PutMapping("/{code}/permissions")
    public RbacDtos.RoleDto update(@PathVariable String code,
                                   @Valid @RequestBody RbacDtos.UpdateRolePermissionsRequest request) {
        return rbacService.updateRolePermissions(code, request.permissions());
    }
}
