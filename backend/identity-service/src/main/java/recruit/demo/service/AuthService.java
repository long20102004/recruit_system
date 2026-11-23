package recruit.demo.service;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.dto.AuthDtos;
import recruit.demo.entity.*;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.UserRepository;
import recruit.demo.security.JwtService;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final AuthenticationManager authenticationManager;
    private final JwtService jwtService;

    @Transactional
    public AuthDtos.AuthResponse register(AuthDtos.RegisterRequest request) {
        if (userRepository.existsByEmailIgnoreCase(request.email())) {
            throw new ApiException(HttpStatus.CONFLICT, "Email đã được đăng ký");
        }

        String email = request.email().trim().toLowerCase();
        User user = User.builder()
                .email(email)
                .passwordHash(passwordEncoder.encode(request.password()))
                .fullName(displayNameFromEmail(email))
                .role(Role.CANDIDATE)
                .roleChosen(false)
                .status(UserStatus.ACTIVE)
                .build();
        userRepository.save(user);

        String token = jwtService.generateToken(user.getId(), user.getEmail(), user.getRole());
        return new AuthDtos.AuthResponse(token, toUserResponse(user));
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

        String token = jwtService.generateToken(user.getId(), user.getEmail(), user.getRole());
        return new AuthDtos.AuthResponse(token, toUserResponse(user));
    }

    public AuthDtos.AuthResponse login(AuthDtos.LoginRequest request) {
        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.email().trim().toLowerCase(), request.password()));
        User user = userRepository.findByEmailIgnoreCase(request.email())
                .orElseThrow(() -> new ApiException(HttpStatus.UNAUTHORIZED, "Invalid email or password"));
        String token = jwtService.generateToken(user.getId(), user.getEmail(), user.getRole());
        return new AuthDtos.AuthResponse(token, toUserResponse(user));
    }

    public AuthDtos.UserResponse me() {
        UserPrincipal principal = SecurityUtils.currentUser();
        User user = userRepository.findById(principal.getId())
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "User not found"));
        return toUserResponse(user);
    }

    private AuthDtos.UserResponse toUserResponse(User user) {
        return new AuthDtos.UserResponse(
                user.getId(), user.getFullName(), user.getEmail(), user.getRole(), user.isRoleChosen());
    }

    private String displayNameFromEmail(String email) {
        int at = email.indexOf('@');
        String local = at > 0 ? email.substring(0, at) : email;
        return local.isBlank() ? email : local;
    }
}
