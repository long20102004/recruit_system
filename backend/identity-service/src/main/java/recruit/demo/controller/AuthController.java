package recruit.demo.controller;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.AuthDtos;
import recruit.demo.service.AuthService;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/login")
    public AuthDtos.AuthResponse login(@Valid @RequestBody AuthDtos.LoginRequest request) {
        return authService.login(request);
    }

    @PostMapping("/register")
    public AuthDtos.RegisterResponse register(@Valid @RequestBody AuthDtos.RegisterRequest request) {
        return authService.register(request);
    }

    @PostMapping("/verify-email")
    public AuthDtos.AuthResponse verifyEmail(@Valid @RequestBody AuthDtos.TokenRequest request) {
        return authService.verifyEmail(request);
    }

    @PostMapping("/resend-verification")
    public AuthDtos.MessageResponse resendVerification(@Valid @RequestBody AuthDtos.EmailRequest request) {
        return authService.resendVerification(request);
    }

    @PostMapping("/forgot-password")
    public AuthDtos.MessageResponse forgotPassword(@Valid @RequestBody AuthDtos.EmailRequest request) {
        return authService.forgotPassword(request);
    }

    @PostMapping("/reset-password")
    public AuthDtos.MessageResponse resetPassword(@Valid @RequestBody AuthDtos.ResetPasswordRequest request) {
        return authService.resetPassword(request);
    }

    @GetMapping("/me")
    public AuthDtos.UserResponse me() {
        return authService.me();
    }

    @PostMapping("/role")
    public AuthDtos.AuthResponse chooseRole(@Valid @RequestBody AuthDtos.ChooseRoleRequest request) {
        return authService.chooseRole(request);
    }
}
