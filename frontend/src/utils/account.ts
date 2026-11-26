import type { UserDto } from "../api/client";
import { hasPermission } from "./permissions";

/** Trang đầu tiên sau đăng nhập, theo quyền của user (specs/004-rbac). */
export function accountPath(user: UserDto): string {
  if (user.roleChosen === false) return "/choose-role";
  if (hasPermission(user, "dashboard:recruiter")) return "/recruiter";
  if (hasPermission(user, "user:read")) return "/admin/users";
  if (hasPermission(user, ["application:read-own", "cv:manage-own"])) return "/candidate";
  // Phòng khi /me chưa trả permissions (token cũ): theo role như trước.
  if (user.role === "RECRUITER" || user.role === "ADMIN") return "/recruiter";
  return "/candidate";
}
