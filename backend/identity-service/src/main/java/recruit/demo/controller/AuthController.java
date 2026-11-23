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
    public AuthDtos.AuthResponse register(@Valid @RequestBody AuthDtos.RegisterRequest request) {
        return authService.register(request);
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
