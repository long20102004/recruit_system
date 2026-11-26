package recruit.demo.controller;

import recruit.demo.dto.auth.AuthResponse;
import recruit.demo.dto.auth.ChooseRoleRequest;
import recruit.demo.dto.auth.EmailRequest;
import recruit.demo.dto.auth.GoogleLoginRequest;
import recruit.demo.dto.auth.LoginRequest;
import recruit.demo.dto.auth.MessageResponse;
import recruit.demo.dto.auth.RegisterRequest;
import recruit.demo.dto.auth.RegisterResponse;
import recruit.demo.dto.auth.ResetPasswordRequest;
import recruit.demo.dto.auth.TokenRequest;
import recruit.demo.dto.auth.UserResponse;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import recruit.demo.dto.BaseResponse;
import org.springframework.web.bind.annotation.*;
import recruit.demo.service.AuthService;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/login")
    public BaseResponse<AuthResponse> login(@Valid @RequestBody LoginRequest request) {
        return BaseResponse.success(authService.login(request));
    }

    @PostMapping("/register")
    public BaseResponse<RegisterResponse> register(@Valid @RequestBody RegisterRequest request) {
        return BaseResponse.success(authService.register(request));
    }

    @PostMapping("/google")
    public BaseResponse<AuthResponse> google(@Valid @RequestBody GoogleLoginRequest request) {
        return BaseResponse.success(authService.googleLogin(request));
    }

    @PostMapping("/verify-email")
    public BaseResponse<AuthResponse> verifyEmail(@Valid @RequestBody TokenRequest request) {
        return BaseResponse.success(authService.verifyEmail(request));
    }

    @PostMapping("/resend-verification")
    public BaseResponse<MessageResponse> resendVerification(@Valid @RequestBody EmailRequest request) {
        return BaseResponse.success(authService.resendVerification(request));
    }

    @PostMapping("/forgot-password")
    public BaseResponse<MessageResponse> forgotPassword(@Valid @RequestBody EmailRequest request) {
        return BaseResponse.success(authService.forgotPassword(request));
    }

    @PostMapping("/reset-password")
    public BaseResponse<MessageResponse> resetPassword(@Valid @RequestBody ResetPasswordRequest request) {
        return BaseResponse.success(authService.resetPassword(request));
    }

    @GetMapping("/me")
    public BaseResponse<UserResponse> me() {
        return BaseResponse.success(authService.me());
    }

    @PostMapping("/role")
    public BaseResponse<AuthResponse> chooseRole(@Valid @RequestBody ChooseRoleRequest request) {
        return BaseResponse.success(authService.chooseRole(request));
    }
}
