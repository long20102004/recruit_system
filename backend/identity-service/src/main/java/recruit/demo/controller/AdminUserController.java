package recruit.demo.controller;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.AdminUserDtos.AdminUserDto;
import recruit.demo.dto.AdminUserDtos.LockRequest;
import recruit.demo.dto.PageResponse;
import recruit.demo.enums.UserStatus;
import recruit.demo.service.AdminUserService;

@RestController
@RequestMapping("/api/admin/users")
@RequiredArgsConstructor
public class AdminUserController {

    private final AdminUserService adminUserService;

    @GetMapping
    public PageResponse<AdminUserDto> list(@RequestParam(required = false) String q,
                                           @RequestParam(required = false) UserStatus status,
                                           @RequestParam(defaultValue = "0") int page,
                                           @RequestParam(defaultValue = "20") int size) {
        return adminUserService.list(q, status, page, size);
    }

    @PatchMapping("/{id}/lock")
    public AdminUserDto lock(@PathVariable Integer id, @Valid @RequestBody LockRequest request) {
        return adminUserService.lock(id, request.reason());
    }

    @PatchMapping("/{id}/unlock")
    public AdminUserDto unlock(@PathVariable Integer id) {
        return adminUserService.unlock(id);
    }
}
