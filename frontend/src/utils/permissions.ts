import type { UserDto } from "../api/client";

/** Quyền yêu cầu: một permission, hoặc danh sách (có một trong số đó là đủ). */
export type PermissionRequirement = string | string[];

/** true nếu user có ít nhất một permission yêu cầu (specs/004-rbac). */
export function hasPermission(user: UserDto | null | undefined, need: PermissionRequirement): boolean {
  const owned = user?.permissions ?? [];
  const list = Array.isArray(need) ? need : [need];
  return list.some((p) => owned.includes(p));
}
