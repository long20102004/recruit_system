package recruit.demo.dto.auth;

/** Quy tắc mật khẩu dùng chung cho đăng ký, đặt lại và đổi mật khẩu. */
public final class PasswordPolicy {

    /** Mật khẩu 8–100 ký tự, có ít nhất một chữ cái và một chữ số. */
    public static final String PATTERN = "^(?=.*[A-Za-z])(?=.*\\d).{8,100}$";
    public static final String MESSAGE = "Mật khẩu cần 8–100 ký tự, gồm cả chữ và số";

    private PasswordPolicy() {
    }
}
