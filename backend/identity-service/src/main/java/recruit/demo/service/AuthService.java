package recruit.demo.service;

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


public interface AuthService {
    RegisterResponse register(RegisterRequest request);
    AuthResponse verifyEmail(TokenRequest request);
    MessageResponse resendVerification(EmailRequest request);
    AuthResponse login(LoginRequest request);
    AuthResponse googleLogin(GoogleLoginRequest request);
    MessageResponse forgotPassword(EmailRequest request);
    MessageResponse resetPassword(ResetPasswordRequest request);
    AuthResponse chooseRole(ChooseRoleRequest request);
    UserResponse me();
}
