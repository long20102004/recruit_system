package recruit.demo.service.impl;

import recruit.demo.dto.admin.MatrixResponse;
import recruit.demo.dto.admin.PermissionDto;
import recruit.demo.dto.admin.RoleDto;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import recruit.demo.entity.AppPermission;
import recruit.demo.entity.AppRole;
import recruit.demo.enums.Role;
import recruit.demo.exception.ApiException;
import recruit.demo.exception.BusinessException;
import recruit.demo.exception.ErrorCode;
import recruit.demo.repository.AppPermissionRepository;
import recruit.demo.repository.AppRoleRepository;
import recruit.demo.security.UserSnapshotCache;
import recruit.demo.service.RbacService;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Ma trận Role → Permission lưu trong DB (specs/004-rbac). Đọc qua cache trong bộ nhớ; sửa ma trận thì xoá cache
 * này và cache tóm tắt user ở Redis để mọi service thấy quyền mới ngay ở request kế tiếp.
 */
@Service
@RequiredArgsConstructor
public class RbacServiceImpl implements RbacService {

    /** Quyền không được gỡ khỏi ADMIN, tránh tự khoá chức năng phân quyền. */
    static final String ROLE_MANAGE = "role:manage";

    private final AppRoleRepository roles;
    private final AppPermissionRepository permissions;
    private final UserSnapshotCache userCache;
    private final Map<Role, List<String>> cache = new ConcurrentHashMap<>();

    @Override
    @Transactional(readOnly = true)
    public List<String> permissionsOf(Role role) {
        if (role == null) return List.of();
        return cache.computeIfAbsent(role, r -> roles.findById(r.name())
                .map(found -> found.getPermissions().stream().map(AppPermission::getCode).sorted().toList())
                .orElse(List.of()));
    }

    @Override
    @Transactional(readOnly = true)
    public MatrixResponse matrix() {
        List<RoleDto> roleDtos = roles.findAll().stream()
                .sorted(Comparator.comparing(r -> roleOrder(r.getCode())))
                .map(RbacServiceImpl::toDto)
                .toList();
        List<PermissionDto> perms = permissions.findAll().stream()
                .sorted(Comparator.comparing(AppPermission::getResource).thenComparing(AppPermission::getCode))
                .map(p -> new PermissionDto(p.getCode(), p.getResource(), p.getDescription()))
                .toList();
        return new MatrixResponse(roleDtos, perms);
    }

    @Override
    @Transactional
    public RoleDto updateRolePermissions(String roleCode, List<String> codes) {
        AppRole role = roles.findById(roleCode == null ? "" : roleCode.trim().toUpperCase(Locale.ROOT))
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Role not found"));
        Set<String> wanted = new TreeSet<>(codes == null ? List.of() : codes);
        if (Role.ADMIN.name().equals(role.getCode()) && !wanted.contains(ROLE_MANAGE)) {
            throw new BusinessException(ErrorCode.BAD_REQUEST,
                    "Không thể gỡ quyền " + ROLE_MANAGE + " khỏi ADMIN", null);
        }
        List<AppPermission> found = permissions.findAllById(wanted);
        if (found.size() != wanted.size()) {
            Set<String> known = new HashSet<>();
            found.forEach(p -> known.add(p.getCode()));
            wanted.removeAll(known);
            throw new BusinessException(ErrorCode.BAD_REQUEST, "Permission không tồn tại: " + String.join(", ", wanted), null);
        }
        role.setPermissions(new HashSet<>(found));
        roles.save(role);
        afterCommit(() -> {
            cache.clear();
            userCache.evictAll();
        });
        return toDto(role);
    }

    private static RoleDto toDto(AppRole r) {
        return new RoleDto(r.getCode(), r.getName(), r.getDescription(),
                r.getPermissions().stream().map(AppPermission::getCode).sorted().toList());
    }

    private static int roleOrder(String code) {
        return switch (code) { case "CANDIDATE" -> 0; case "RECRUITER" -> 1; case "ADMIN" -> 2; default -> 3; };
    }

    private static void afterCommit(Runnable action) {
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override
                public void afterCommit() {
                    action.run();
                }
            });
        } else {
            action.run();
        }
    }
}
