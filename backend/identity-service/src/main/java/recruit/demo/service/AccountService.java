package recruit.demo.service;

import recruit.demo.dto.AccountDtos;
import recruit.demo.dto.AuthDtos;

/** Tài khoản của chính người dùng đang đăng nhập (màn C14). */
public interface AccountService {
    AccountDtos.ProfileResponse profile();
    AccountDtos.ProfileResponse updateProfile(AccountDtos.UpdateProfileRequest request);
    /** Đổi mật khẩu, vô hiệu các phiên khác, trả token mới cho phiên hiện tại. */
    AuthDtos.AuthResponse changePassword(AccountDtos.ChangePasswordRequest request);
    AccountDtos.NotificationSettings notificationSettings();
    AccountDtos.NotificationSettings updateNotificationSettings(AccountDtos.NotificationSettings request);
}
