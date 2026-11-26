package recruit.demo.service.impl;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.config.AuthProperties;
import recruit.demo.dto.AccountDtos;
import recruit.demo.dto.AuthDtos;
import recruit.demo.entity.NotificationPreference;
import recruit.demo.entity.User;
import recruit.demo.enums.NotificationType;
import recruit.demo.exception.ApiException;
import recruit.demo.exception.BusinessException;
import recruit.demo.exception.ErrorCode;
import recruit.demo.repository.NotificationPreferenceRepository;
import recruit.demo.repository.UserRepository;
import recruit.demo.security.JwtService;
import recruit.demo.security.SecurityUtils;
import recruit.demo.service.AccountService;
import recruit.demo.service.LoginAttemptService;
import recruit.demo.service.RbacService;
import recruit.demo.service.UserCacheInvalidator;

import java.util.Arrays;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/** specs/006-account-settings: hồ sơ, đổi mật khẩu, cài đặt thông báo của chính người dùng. */
@Service
@RequiredArgsConstructor
public class AccountServiceImpl implements AccountService {

    private final UserRepository users;
    private final NotificationPreferenceRepository prefs;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final LoginAttemptService loginAttempts;
    private final AuthProperties props;
    private final UserCacheInvalidator userCache;
    private final RbacService rbac;

    @Override
    public AccountDtos.ProfileResponse profile() {
        return toProfile(currentUser());
    }

    @Override
    @Transactional
    public AccountDtos.ProfileResponse updateProfile(AccountDtos.UpdateProfileRequest request) {
        User user = currentUser();
        user.setFullName(request.fullName().trim());
        user.setPhone(blankToNull(request.phone()));
        user.setDateOfBirth(request.dateOfBirth());
        user.setGender(request.gender());
        User saved = users.save(user);
        userCache.evictAfterCommit(saved.getId());
        return toProfile(saved);
    }

    /**
     * Sai mật khẩu hiện tại được đếm chung bộ đếm đăng nhập sai theo email (Redis),
     * để không dùng màn này dò mật khẩu thay cho màn đăng nhập.
     */
    @Override
    @Transactional
    public AuthDtos.AuthResponse changePassword(AccountDtos.ChangePasswordRequest request) {
        User user = currentUser();
        String email = AuthServiceImpl.normalize(user.getEmail());
        if (user.isPasswordSet()) {
            loginAttempts.lockedForSeconds(email).ifPresent(seconds -> {
                throw tooManyAttempts(seconds);
            });
            String current = request.currentPassword();
            if (current == null || current.isEmpty() || !passwordEncoder.matches(current, user.getPasswordHash())) {
                if (loginAttempts.recordFailure(email)) {
                    throw tooManyAttempts(props.getLoginLockDuration().toSeconds());
                }
                throw new BusinessException(ErrorCode.WRONG_CURRENT_PASSWORD);
            }
            if (passwordEncoder.matches(request.newPassword(), user.getPasswordHash())) {
                throw new ApiException(HttpStatus.BAD_REQUEST, "Mật khẩu mới phải khác mật khẩu hiện tại");
            }
            loginAttempts.reset(email);
        }
        user.setPasswordHash(passwordEncoder.encode(request.newPassword()));
        user.setPasswordSet(true);
        user.invalidateSessions();
        User saved = users.save(user);
        userCache.evictAfterCommit(saved.getId());
        // iat của token mới >= mốc vô hiệu (cùng giây) nên phiên hiện tại vẫn dùng được.
        String token = jwtService.generateToken(saved.getId(), saved.getEmail(), saved.getRole());
        return new AuthDtos.AuthResponse(token, new AuthDtos.UserResponse(
                saved.getId(), saved.getFullName(), saved.getEmail(), saved.getRole(), saved.isRoleChosen(),
                rbac.permissionsOf(saved.getRole())));
    }

    @Override
    public AccountDtos.NotificationSettings notificationSettings() {
        return settingsOf(currentUser().getId());
    }

    @Override
    @Transactional
    public AccountDtos.NotificationSettings updateNotificationSettings(AccountDtos.NotificationSettings request) {
        Integer userId = currentUser().getId();
        Map<NotificationType, NotificationPreference> existing = prefs.findByUserId(userId).stream()
                .collect(Collectors.toMap(NotificationPreference::getType, Function.identity()));
        for (AccountDtos.NotificationPreference p : request.items()) {
            NotificationPreference row = existing.get(p.type());
            if (row == null) {
                row = new NotificationPreference(userId, p.type(), p.inApp(), p.email());
                existing.put(p.type(), row);
            } else {
                row.setInApp(p.inApp());
                row.setEmail(p.email());
            }
        }
        prefs.saveAll(existing.values());
        return settingsOf(userId);
    }

    private AccountDtos.NotificationSettings settingsOf(Integer userId) {
        Map<NotificationType, NotificationPreference> saved = new EnumMap<>(NotificationType.class);
        prefs.findByUserId(userId).forEach(p -> saved.put(p.getType(), p));
        List<AccountDtos.NotificationPreference> items = Arrays.stream(NotificationType.values())
                .map(t -> {
                    NotificationPreference p = saved.get(t);
                    return p == null
                            ? new AccountDtos.NotificationPreference(t, t.defaultInApp(), t.defaultEmail())
                            : new AccountDtos.NotificationPreference(t, p.isInApp(), p.isEmail());
                })
                .toList();
        return new AccountDtos.NotificationSettings(items);
    }

    private User currentUser() {
        Integer id = SecurityUtils.currentUser().getId();
        return users.findById(id).orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "User not found"));
    }

    private static AccountDtos.ProfileResponse toProfile(User u) {
        return new AccountDtos.ProfileResponse(u.getId(), u.getFullName(), u.getEmail(), u.getPhone(),
                u.getDateOfBirth(), u.getGender(), u.getRole(), u.isPasswordSet(), u.getGoogleSub() != null);
    }

    private static String blankToNull(String s) {
        return s == null || s.isBlank() ? null : s.trim();
    }

    private static BusinessException tooManyAttempts(long seconds) {
        long minutes = Math.max(1, (seconds + 59) / 60);
        return new BusinessException(ErrorCode.LOGIN_TEMPORARILY_LOCKED,
                "Nhập sai mật khẩu quá nhiều lần. Vui lòng thử lại sau " + minutes + " phút.",
                Map.of("retryAfterSeconds", seconds));
    }
}
