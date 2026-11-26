package recruit.demo.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Past;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import recruit.demo.enums.Gender;
import recruit.demo.enums.NotificationType;
import recruit.demo.enums.Role;

import java.time.LocalDate;
import java.util.List;

/** Tài khoản của người dùng đang đăng nhập (specs/006-account-settings, màn C14). */
public final class AccountDtos {

    private AccountDtos() {
    }

    /** passwordSet = false: tài khoản tạo bằng Google chưa đặt mật khẩu. */
    public record ProfileResponse(
            Integer id,
            String fullName,
            String email,
            String phone,
            LocalDate dateOfBirth,
            Gender gender,
            Role role,
            boolean passwordSet,
            boolean googleLinked
    ) {
    }

    public record UpdateProfileRequest(
            @NotBlank(message = "Vui lòng nhập họ tên") @Size(max = 100, message = "Họ tên tối đa 100 ký tự") String fullName,
            @Pattern(regexp = "^$|^\\+?[0-9 .-]{8,20}$", message = "Số điện thoại không hợp lệ") String phone,
            @Past(message = "Ngày sinh phải trước hôm nay") LocalDate dateOfBirth,
            Gender gender
    ) {
    }

    /** currentPassword bắt buộc khi tài khoản đã có mật khẩu (passwordSet). */
    public record ChangePasswordRequest(
            @Size(max = 200) String currentPassword,
            @NotBlank @Pattern(regexp = AuthDtos.PASSWORD_PATTERN, message = AuthDtos.PASSWORD_MESSAGE) String newPassword
    ) {
    }

    public record NotificationPreference(
            @NotNull NotificationType type,
            boolean inApp,
            boolean email
    ) {
    }

    public record NotificationSettings(
            @NotNull @Size(max = 20) List<@Valid @NotNull NotificationPreference> items
    ) {
    }
}
