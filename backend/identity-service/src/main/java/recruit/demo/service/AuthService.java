package recruit.demo.service;

import recruit.demo.dto.AuthDtos;

public interface AuthService {
    AuthDtos.RegisterResponse register(AuthDtos.RegisterRequest request);
    AuthDtos.AuthResponse verifyEmail(AuthDtos.TokenRequest request);
    AuthDtos.MessageResponse resendVerification(AuthDtos.EmailRequest request);
    AuthDtos.AuthResponse login(AuthDtos.LoginRequest request);
    AuthDtos.AuthResponse googleLogin(AuthDtos.GoogleLoginRequest request);
    AuthDtos.MessageResponse forgotPassword(AuthDtos.EmailRequest request);
    AuthDtos.MessageResponse resetPassword(AuthDtos.ResetPasswordRequest request);
    AuthDtos.AuthResponse chooseRole(AuthDtos.ChooseRoleRequest request);
    AuthDtos.UserResponse me();
}
