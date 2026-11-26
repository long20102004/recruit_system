package recruit.demo.service.impl;

import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.admin.AdminUserDto;
import recruit.demo.entity.AuditLog;
import recruit.demo.entity.User;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
import recruit.demo.exception.ApiException;
import recruit.demo.exception.BusinessException;
import recruit.demo.exception.ErrorCode;
import recruit.demo.repository.AuditLogRepository;
import recruit.demo.repository.UserRepository;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;
import recruit.demo.service.AdminUserService;
import recruit.demo.service.UserCacheInvalidator;

import java.time.LocalDateTime;

/** Admin xem danh sách, khoá / mở khoá tài khoản. Khoá vô hiệu mọi phiên và xoá cache để có hiệu lực ngay. */
@Service
@RequiredArgsConstructor
public class AdminUserServiceImpl implements AdminUserService {

    private static final int MAX_PAGE_SIZE = 100;

    private final UserRepository users;
    private final UserCacheInvalidator userCache;
    private final AuditLogRepository auditLogs;

    @Transactional(readOnly = true)
    public PageResponse<AdminUserDto> list(String q, UserStatus status, int page, int size) {
        String keyword = q == null || q.isBlank() ? null : q.trim();
        var pageable = PageRequest.of(Math.max(page, 0), Math.min(Math.max(size, 1), MAX_PAGE_SIZE),
                Sort.by(Sort.Direction.DESC, "id"));
        return PageResponse.toPageResponse(users.search(keyword, status, pageable).map(AdminUserServiceImpl::toDto));
    }

    @Transactional
    public AdminUserDto lock(Integer id, String reason) {
        User user = require(id);
        UserPrincipal actor = SecurityUtils.currentUser();
        if (user.getId().equals(actor.getId()) || user.getRole() == Role.ADMIN) {
            throw new BusinessException(ErrorCode.CANNOT_LOCK_USER,
                    "Không thể khoá tài khoản của chính bạn hoặc tài khoản quản trị", null);
        }
        user.setStatus(UserStatus.BANNED);
        user.setLockedReason(reason.trim());
        user.setLockedAt(LocalDateTime.now());
        user.invalidateSessions();
        users.save(user);
        userCache.evictAfterCommit(user.getId());
        auditLogs.save(AuditLog.builder()
                .eventType("LOCK_USER")
                .eventLabel("Khoá tài khoản")
                .badgeClass("badge b-danger")
                .target(user.getEmail())
                .actorUserId(actor.getId())
                .actorEmail(actor.getEmail())
                .build());
        return toDto(user);
    }

    @Transactional
    public AdminUserDto unlock(Integer id) {
        User user = require(id);
        UserPrincipal actor = SecurityUtils.currentUser();
        if (user.getStatus() == UserStatus.BANNED) {
            user.setStatus(UserStatus.ACTIVE);
            user.setLockedReason(null);
            user.setLockedAt(null);
            users.save(user);
            userCache.evictAfterCommit(user.getId());
            auditLogs.save(AuditLog.builder()
                    .eventType("UNLOCK_USER")
                    .eventLabel("Mở khoá tài khoản")
                    .badgeClass("badge b-ok")
                    .target(user.getEmail())
                    .actorUserId(actor.getId())
                    .actorEmail(actor.getEmail())
                    .build());
        }
        return toDto(user);
    }

    private User require(Integer id) {
        return users.findById(id).orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "User not found"));
    }

    static AdminUserDto toDto(User u) {
        return new AdminUserDto(u.getId(), u.getFullName(), u.getEmail(), u.getRole(), u.getStatus(),
                u.emailVerified(), u.getLockedReason(), u.getLockedAt(), u.getCreatedAt());
    }
}
