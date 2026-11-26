package recruit.demo.controller;

import recruit.demo.dto.admin.AdminUserDto;
import recruit.demo.dto.admin.LockRequest;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import recruit.demo.dto.BaseResponse;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.PageResponse;
import recruit.demo.enums.UserStatus;
import recruit.demo.service.AdminUserService;

@RestController
@RequestMapping("/api/admin/users")
@RequiredArgsConstructor
public class AdminUserController {

    private final AdminUserService adminUserService;

    @GetMapping
    @PreAuthorize("hasAuthority('user:read')")
    public BaseResponse<PageResponse<AdminUserDto>> list(@RequestParam(required = false) String q,
                                           @RequestParam(required = false) UserStatus status,
                                           @RequestParam(defaultValue = "0") int page,
                                           @RequestParam(defaultValue = "20") int size) {
        return BaseResponse.success(adminUserService.list(q, status, page, size));
    }

    @PatchMapping("/{id}/lock")
    @PreAuthorize("hasAuthority('user:lock')")
    public BaseResponse<AdminUserDto> lock(@PathVariable Integer id, @Valid @RequestBody LockRequest request) {
        return BaseResponse.success(adminUserService.lock(id, request.getReason()));
    }

    @PatchMapping("/{id}/unlock")
    @PreAuthorize("hasAuthority('user:lock')")
    public BaseResponse<AdminUserDto> unlock(@PathVariable Integer id) {
        return BaseResponse.success(adminUserService.unlock(id));
    }
}
