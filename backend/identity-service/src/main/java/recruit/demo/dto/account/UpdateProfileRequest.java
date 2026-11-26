package recruit.demo.dto.account;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Past;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import recruit.demo.enums.Gender;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UpdateProfileRequest {
    @NotBlank(message = "Vui lòng nhập họ tên") @Size(max = 100, message = "Họ tên tối đa 100 ký tự")
    private String fullName;
    @Pattern(regexp = "^$|^\\+?[0-9 .-]{8,20}$", message = "Số điện thoại không hợp lệ")
    private String phone;
    @Past(message = "Ngày sinh phải trước hôm nay")
    private LocalDate dateOfBirth;
    private Gender gender;
}
