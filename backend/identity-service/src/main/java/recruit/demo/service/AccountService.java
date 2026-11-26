package recruit.demo.service;

import recruit.demo.dto.auth.AuthResponse;
import recruit.demo.dto.account.ChangePasswordRequest;
import recruit.demo.dto.account.NotificationSettingsDto;
import recruit.demo.dto.account.ProfileResponse;
import recruit.demo.dto.account.UpdateProfileRequest;


/** Tài khoản của chính người dùng đang đăng nhập (màn C14). */
public interface AccountService {
    ProfileResponse profile();
    ProfileResponse updateProfile(UpdateProfileRequest request);
    /** Đổi mật khẩu, vô hiệu các phiên khác, trả token mới cho phiên hiện tại. */
    AuthResponse changePassword(ChangePasswordRequest request);
    NotificationSettingsDto notificationSettings();
    NotificationSettingsDto updateNotificationSettings(NotificationSettingsDto request);
}
