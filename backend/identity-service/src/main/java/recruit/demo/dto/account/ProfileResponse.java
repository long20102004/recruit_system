package recruit.demo.dto.account;

import recruit.demo.enums.Gender;
import recruit.demo.enums.Role;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

/** Hồ sơ của người dùng đang đăng nhập (màn C14). passwordSet = false: tài khoản tạo bằng Google chưa đặt mật khẩu. */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProfileResponse {
    private Integer id;
    private String fullName;
    private String email;
    private String phone;
    private LocalDate dateOfBirth;
    private Gender gender;
    private Role role;
    private boolean passwordSet;
    private boolean googleLinked;
}
