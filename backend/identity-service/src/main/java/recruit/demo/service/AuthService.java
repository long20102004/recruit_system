package recruit.demo.service;

import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.config.AuthProperties;
import recruit.demo.dto.AuthDtos;
import recruit.demo.entity.*;
import recruit.demo.exception.ApiException;
import recruit.demo.exception.BusinessException;
import recruit.demo.exception.ErrorCode;
import recruit.demo.repository.UserRepository;
import recruit.demo.security.JwtService;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;
import recruit.demo.service.OneTimeTokenService.Purpose;

import java.time.LocalDateTime;
import java.util.Locale;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class AuthService {

    static final String RESEND_MESSAGE = "Nếu email cần xác thực, bạn sẽ nhận được email mới trong ít phút.";
    static final String FORGOT_MESSAGE = "Nếu email tồn tại, bạn sẽ nhận được link đặt lại mật khẩu trong ít phút.";

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final AuthProperties props;
    private final LoginAttemptService loginAttempts;
    private final OneTimeTokenService tokens;
    private final AuthMailService mail;
    private final UserCacheInvalidator userCache;

    /** Băm giả để email không tồn tại vẫn tốn thời gian so khớp như email có thật. */
    private volatile String dummyHash;

    /** Tạo tài khoản chưa xác thực và gửi link xác thực; không cấp token đăng nhập. */
    public AuthDtos.RegisterResponse register(AuthDtos.RegisterRequest request) {
        String email = normalize(request.email());
        if (userRepository.existsByEmailIgnoreCase(email)) {
            throw new BusinessException(ErrorCode.EMAIL_ALREADY_EXISTS, "Email đã được đăng ký", null);
        }
        User user = userRepository.save(User.builder()
                .email(email)
                .passwordHash(passwordEncoder.encode(request.password()))
                .fullName(displayNameFromEmail(email))
                .role(Role.CANDIDATE)
                .roleChosen(false)
                .status(UserStatus.ACTIVE)
                .build());

        tokens.tryAcquireCooldown(Purpose.VERIFY, email, props.getResendCooldown());
        String token = tokens.issue(Purpose.VERIFY, user.getId(), props.getVerifyTokenTtl());
        mail.sendVerification(email, user.getFullName(), token);
        return new AuthDtos.RegisterResponse(email,
                "Đã gửi email xác thực tới " + email + ". Vui lòng kiểm tra hộp thư để kích hoạt tài khoản.");
    }

    /** Bấm link xác thực: đánh dấu đã xác thực và đăng nhập luôn. */
    @Transactional
    public AuthDtos.AuthResponse verifyEmail(AuthDtos.TokenRequest request) {
        Integer userId = tokens.consume(Purpose.VERIFY, request.token())
                .orElseThrow(() -> new BusinessException(ErrorCode.INVALID_LINK_TOKEN));
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new BusinessException(ErrorCode.INVALID_LINK_TOKEN));
        requireNotLocked(user);
        if (!user.emailVerified()) {
            user.setEmailVerifiedAt(LocalDateTime.now());
            userRepository.save(user);
        }
        return issueSession(user);
    }

    public AuthDtos.MessageResponse resendVerification(AuthDtos.EmailRequest request) {
        String email = normalize(request.email());
        userRepository.findByEmailIgnoreCase(email)
                .filter(u -> !u.emailVerified() && u.getStatus() == UserStatus.ACTIVE)
                .filter(u -> tokens.tryAcquireCooldown(Purpose.VERIFY, email, props.getResendCooldown()))
                .ifPresent(u -> mail.sendVerification(email, u.getFullName(),
                        tokens.issue(Purpose.VERIFY, u.getId(), props.getVerifyTokenTtl())));
        return new AuthDtos.MessageResponse(RESEND_MESSAGE);
    }

    /**
     * Thứ tự kiểm tra: khoá tạm → mật khẩu → trạng thái tài khoản.
     * Trạng thái (chưa xác thực, bị khoá) chỉ lộ ra khi mật khẩu đúng.
     */
    public AuthDtos.AuthResponse login(AuthDtos.LoginRequest request) {
        String email = normalize(request.email());
        loginAttempts.lockedForSeconds(email).ifPresent(seconds -> {
            throw temporarilyLocked(seconds);
        });

        User user = userRepository.findByEmailIgnoreCase(email).orElse(null);
        boolean passwordOk;
        if (user != null) {
            passwordOk = passwordEncoder.matches(request.password(), user.getPasswordHash());
        } else {
            passwordEncoder.matches(request.password(), dummyHash());
            passwordOk = false;
        }
        if (!passwordOk) {
            if (loginAttempts.recordFailure(email)) {
                throw temporarilyLocked(props.getLoginLockDuration().toSeconds());
            }
            throw new BusinessException(ErrorCode.INVALID_CREDENTIALS, "Email hoặc mật khẩu không đúng", null);
        }

        loginAttempts.reset(email);
        requireNotLocked(user);
        if (!user.emailVerified()) {
            throw new BusinessException(ErrorCode.EMAIL_NOT_VERIFIED,
                    "Email chưa được xác thực. Vui lòng bấm link trong email hoặc gửi lại email xác thực.",
                    Map.of("email", email));
        }
        return issueSession(user);
    }

    public AuthDtos.MessageResponse forgotPassword(AuthDtos.EmailRequest request) {
        String email = normalize(request.email());
        userRepository.findByEmailIgnoreCase(email)
                .filter(u -> u.getStatus() == UserStatus.ACTIVE)
                .filter(u -> tokens.tryAcquireCooldown(Purpose.RESET, email, props.getResendCooldown()))
                .ifPresent(u -> mail.sendPasswordReset(email, u.getFullName(),
                        tokens.issue(Purpose.RESET, u.getId(), props.getResetTokenTtl())));
        return new AuthDtos.MessageResponse(FORGOT_MESSAGE);
    }

    /** Đổi mật khẩu, vô hiệu mọi phiên cũ, gỡ khoá tạm; link đặt lại cũng chứng minh sở hữu email. */
    @Transactional
    public AuthDtos.MessageResponse resetPassword(AuthDtos.ResetPasswordRequest request) {
        Integer userId = tokens.consume(Purpose.RESET, request.token())
                .orElseThrow(() -> new BusinessException(ErrorCode.INVALID_LINK_TOKEN));
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new BusinessException(ErrorCode.INVALID_LINK_TOKEN));
        requireNotLocked(user);
        user.setPasswordHash(passwordEncoder.encode(request.newPassword()));
        if (!user.emailVerified()) user.setEmailVerifiedAt(LocalDateTime.now());
        user.invalidateSessions();
        userRepository.save(user);
        loginAttempts.clear(normalize(user.getEmail()));
        userCache.evictAfterCommit(user.getId());
        return new AuthDtos.MessageResponse("Đã đặt lại mật khẩu. Vui lòng đăng nhập bằng mật khẩu mới.");
    }

    @Transactional
    public AuthDtos.AuthResponse chooseRole(AuthDtos.ChooseRoleRequest request) {
        if (request.role() != Role.CANDIDATE && request.role() != Role.RECRUITER) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Chỉ được chọn ứng viên hoặc nhà tuyển dụng");
        }
        UserPrincipal principal = SecurityUtils.currentUser();
        User user = userRepository.findById(principal.getId())
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "User not found"));
        if (user.isRoleChosen()) {
            throw new ApiException(HttpStatus.CONFLICT, "Vai trò đã được lưu");
        }

        user.setRole(request.role());
        user.setRoleChosen(true);
        userRepository.save(user);
        userCache.evictAfterCommit(user.getId());

        return issueSession(user);
    }

    public AuthDtos.UserResponse me() {
        UserPrincipal principal = SecurityUtils.currentUser();
        User user = userRepository.findById(principal.getId())
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "User not found"));
        return toUserResponse(user);
    }

    private AuthDtos.AuthResponse issueSession(User user) {
        String token = jwtService.generateToken(user.getId(), user.getEmail(), user.getRole());
        return new AuthDtos.AuthResponse(token, toUserResponse(user));
    }

    private static void requireNotLocked(User user) {
        if (user.getStatus() != UserStatus.ACTIVE) {
            throw new BusinessException(ErrorCode.ACCOUNT_LOCKED,
                    "Tài khoản đã bị khoá. Vui lòng liên hệ quản trị viên.", null);
        }
    }

    private static BusinessException temporarilyLocked(long seconds) {
        long minutes = Math.max(1, (seconds + 59) / 60);
        return new BusinessException(ErrorCode.LOGIN_TEMPORARILY_LOCKED,
                "Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau " + minutes + " phút.",
                Map.of("retryAfterSeconds", seconds));
    }

    private String dummyHash() {
        String h = dummyHash;
        if (h == null) {
            h = passwordEncoder.encode("timing-equalizer-" + System.nanoTime());
            dummyHash = h;
        }
        return h;
    }

    private AuthDtos.UserResponse toUserResponse(User user) {
        return new AuthDtos.UserResponse(
                user.getId(), user.getFullName(), user.getEmail(), user.getRole(), user.isRoleChosen());
    }

    static String normalize(String email) {
        return email == null ? "" : email.trim().toLowerCase(Locale.ROOT);
    }

    private String displayNameFromEmail(String email) {
        int at = email.indexOf('@');
        String local = at > 0 ? email.substring(0, at) : email;
        return local.isBlank() ? email : local;
    }
}
