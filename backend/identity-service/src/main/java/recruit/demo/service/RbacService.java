package recruit.demo.service;

import recruit.demo.dto.RbacDtos;
import recruit.demo.enums.Role;

import java.util.List;

public interface RbacService {
    /** Permission của một role theo ma trận trong DB (có cache trong bộ nhớ). */
    List<String> permissionsOf(Role role);

    RbacDtos.MatrixResponse matrix();

    RbacDtos.RoleDto updateRolePermissions(String roleCode, List<String> permissions);
}
