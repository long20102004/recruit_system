package recruit.demo.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;
import recruit.demo.config.AuthProperties;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

/** Gửi mail xác thực và đặt lại mật khẩu. Lỗi gửi chỉ ghi log (không ghi link / token). */
@Slf4j
@Service
@RequiredArgsConstructor
public class AuthMailService {

    private final JavaMailSender mailSender;
    private final AuthProperties props;

    public void sendVerification(String to, String fullName, String token) {
        String link = link("/verify-email", token);
        send(to, "Xác thực email tài khoản HireLens",
                "Chào " + fullName + ",\n\n"
                + "Bấm vào link sau để xác thực email và kích hoạt tài khoản HireLens:\n" + link + "\n\n"
                + "Link có hiệu lực " + props.getVerifyTokenTtl().toHours() + " giờ và chỉ dùng được một lần.\n"
                + "Nếu bạn không đăng ký tài khoản, hãy bỏ qua email này.\n\nHireLens");
    }

    public void sendPasswordReset(String to, String fullName, String token) {
        String link = link("/reset-password", token);
        send(to, "Đặt lại mật khẩu HireLens",
                "Chào " + fullName + ",\n\n"
                + "Bấm vào link sau để đặt mật khẩu mới:\n" + link + "\n\n"
                + "Link có hiệu lực " + props.getResetTokenTtl().toMinutes() + " phút và chỉ dùng được một lần.\n"
                + "Nếu bạn không yêu cầu đặt lại mật khẩu, hãy bỏ qua email này; mật khẩu hiện tại vẫn giữ nguyên.\n\nHireLens");
    }

    private String link(String path, String token) {
        String base = props.getFrontendUrl().replaceAll("/+$", "");
        return base + path + "?token=" + URLEncoder.encode(token, StandardCharsets.UTF_8);
    }

    private void send(String to, String subject, String body) {
        try {
            SimpleMailMessage msg = new SimpleMailMessage();
            msg.setFrom(props.getMailFrom());
            msg.setTo(to);
            msg.setSubject(subject);
            msg.setText(body);
            mailSender.send(msg);
        } catch (RuntimeException ex) {
            log.warn("Sending '{}' mail failed: {}", subject, ex.getClass().getSimpleName());
        }
    }
}
