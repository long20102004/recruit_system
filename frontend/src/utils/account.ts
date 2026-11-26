import type { UserDto } from "../api/client";
import { hasPermission } from "./permissions";

/** Trang đầu tiên sau đăng nhập, theo quyền của user (specs/004-rbac). */
export function accountPath(user: UserDto): string {
  if (user.roleChosen === false) return "/choose-role";
  if (hasPermission(user, "dashboard:recruiter")) return "/recruiter";
  if (hasPermission(user, "user:read")) return "/admin";
  if (hasPermission(user, ["application:read-own", "cv:manage-own"])) return "/candidate";
  // Phòng khi /me chưa trả permissions (token cũ): theo role như trước.
  if (user.role === "RECRUITER" || user.role === "ADMIN") return "/recruiter";
  return "/candidate";
}

/** Chỉ nhận đường dẫn nội bộ ("/..."), chặn "//host" và "/\host" để không bị chuyển hướng ra trang ngoài. */
function safeRedirect(raw: string | null | undefined): string | null {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//") || raw.startsWith("/\\")) return null;
  return raw;
}

/** Trang đăng nhập kèm đường dẫn cần quay lại sau khi đăng nhập. */
export function loginPath(redirect: string): string {
  return `/login?redirect=${encodeURIComponent(redirect)}`;
}

/** Sau đăng nhập: chưa chọn vai trò thì chọn trước, có ?redirect hợp lệ thì quay lại đó, không thì về trang theo quyền. */
export function afterLoginPath(user: UserDto, redirect: string | null | undefined): string {
  if (user.roleChosen === false) return "/choose-role";
  return safeRedirect(redirect) ?? accountPath(user);
}
