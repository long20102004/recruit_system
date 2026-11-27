package recruit.demo.controller;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.ServiceDtos.*;
import recruit.demo.entity.NotificationPreference;
import recruit.demo.entity.User;
import recruit.demo.enums.NotificationType;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.NotificationPreferenceRepository;
import recruit.demo.repository.UserRepository;
import recruit.demo.security.UserSnapshotCache;
@RestController
@RequestMapping("/internal/users")
@RequiredArgsConstructor
public class InternalUserController {
    private final UserRepository users;
    private final UserSnapshotCache userCache;
    private final recruit.demo.service.RbacService rbac;
    private final NotificationPreferenceRepository notificationPreferences;
    @GetMapping("/{id}")
    public UserSnapshot get(@PathVariable Integer id) { return snapshot(require(id)); }
    @GetMapping("/{id}/notification-context")
    public NotificationContext notificationContext(@PathVariable Integer id,
                                                   @RequestParam NotificationType type) {
        User user = require(id);
        NotificationPreference pref = notificationPreferences
                .findById(new NotificationPreference.Key(id, type))
                .orElse(null);
        boolean inApp = pref != null ? pref.isInApp() : type.defaultInApp();
        boolean emailEnabled = pref != null ? pref.isEmail() : type.defaultEmail();
        return new NotificationContext(user.getId(), user.getEmail(), user.getFullName(), inApp, emailEnabled);
    }
    @PatchMapping("/{id}")
    @Transactional
    public UserSnapshot update(@PathVariable Integer id, @RequestBody ProfileUpdate update) {
        User user = require(id);
        if (update.fullName() != null && !update.fullName().isBlank()) user.setFullName(update.fullName());
        if (update.phone() != null) user.setPhone(update.phone());
        UserSnapshot saved = snapshot(users.save(user));
        userCache.evict(id);
        return saved;
    }
    private User require(Integer id) { return users.findById(id)
        .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "User not found")); }
    private UserSnapshot snapshot(User u) {
        return new UserSnapshot(u.getId(), u.getFullName(), u.getEmail(), u.getPhone(), u.getRole(), u.getStatus(),
            u.sessionsValidAfterEpochSeconds(), rbac.permissionsOf(u.getRole()));
    }
}
