package recruit.demo.service;

/** Xác minh ID token Google Identity Services (specs/005-google-login). */
public interface GoogleTokenVerifier {

    /** Thông tin cần dùng trong ID token Google. */
    record GoogleIdentity(String subject, String email, boolean emailVerified, String name) {
    }

    /**
     * @throws recruit.demo.exception.BusinessException GOOGLE_TOKEN_INVALID nếu token sai / hết hạn / không cấp cho
     *         ứng dụng này; SERVICE_UNAVAILABLE nếu chưa cấu hình Client ID
     */
    GoogleIdentity verify(String credential);
}
