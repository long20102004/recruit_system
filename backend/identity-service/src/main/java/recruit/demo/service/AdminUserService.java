package recruit.demo.service;

import recruit.demo.dto.admin.AdminUserDto;

import recruit.demo.dto.PageResponse;
import recruit.demo.enums.UserStatus;

public interface AdminUserService {
    PageResponse<AdminUserDto> list(String q, UserStatus status, int page, int size);
    AdminUserDto lock(Integer id, String reason);
    AdminUserDto unlock(Integer id);
}
