package recruit.demo.service;

import recruit.demo.dto.admin.MatrixResponse;
import recruit.demo.dto.admin.RoleDto;

import recruit.demo.enums.Role;

import java.util.List;

public interface RbacService {
    /** Permission của một role theo ma trận trong DB (có cache trong bộ nhớ). */
    List<String> permissionsOf(Role role);

    MatrixResponse matrix();

    RoleDto updateRolePermissions(String roleCode, List<String> permissions);
}
