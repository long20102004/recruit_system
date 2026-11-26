package recruit.demo.controller;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.AccountDtos;
import recruit.demo.dto.AuthDtos;
import recruit.demo.service.AccountService;

/** Tài khoản của chính người dùng đang đăng nhập (màn C14). Mọi vai trò đều dùng được. */
@RestController
@RequestMapping("/api/account")
@RequiredArgsConstructor
public class AccountController {

    private final AccountService accountService;

    @GetMapping("/profile")
    public AccountDtos.ProfileResponse profile() {
        return accountService.profile();
    }

    @PutMapping("/profile")
    public AccountDtos.ProfileResponse updateProfile(@Valid @RequestBody AccountDtos.UpdateProfileRequest request) {
        return accountService.updateProfile(request);
    }

    @PostMapping("/password")
    public AuthDtos.AuthResponse changePassword(@Valid @RequestBody AccountDtos.ChangePasswordRequest request) {
        return accountService.changePassword(request);
    }

    @GetMapping("/notifications")
    public AccountDtos.NotificationSettings notifications() {
        return accountService.notificationSettings();
    }

    @PutMapping("/notifications")
    public AccountDtos.NotificationSettings updateNotifications(
            @Valid @RequestBody AccountDtos.NotificationSettings request) {
        return accountService.updateNotificationSettings(request);
    }
}
