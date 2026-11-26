package recruit.demo.controller;

import recruit.demo.dto.auth.AuthResponse;
import recruit.demo.dto.account.ChangePasswordRequest;
import recruit.demo.dto.account.NotificationSettingsDto;
import recruit.demo.dto.account.ProfileResponse;
import recruit.demo.dto.account.UpdateProfileRequest;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import recruit.demo.dto.BaseResponse;
import org.springframework.web.bind.annotation.*;
import recruit.demo.service.AccountService;

/** Tài khoản của chính người dùng đang đăng nhập (màn C14). Mọi vai trò đều dùng được. */
@RestController
@RequestMapping("/api/account")
@RequiredArgsConstructor
public class AccountController {

    private final AccountService accountService;

    @GetMapping("/profile")
    public BaseResponse<ProfileResponse> profile() {
        return BaseResponse.success(accountService.profile());
    }

    @PutMapping("/profile")
    public BaseResponse<ProfileResponse> updateProfile(@Valid @RequestBody UpdateProfileRequest request) {
        return BaseResponse.success(accountService.updateProfile(request));
    }

    @PostMapping("/password")
    public BaseResponse<AuthResponse> changePassword(@Valid @RequestBody ChangePasswordRequest request) {
        return BaseResponse.success(accountService.changePassword(request));
    }

    @GetMapping("/notifications")
    public BaseResponse<NotificationSettingsDto> notifications() {
        return BaseResponse.success(accountService.notificationSettings());
    }

    @PutMapping("/notifications")
    public BaseResponse<NotificationSettingsDto> updateNotifications(
            @Valid @RequestBody NotificationSettingsDto request) {
        return BaseResponse.success(accountService.updateNotificationSettings(request));
    }
}
