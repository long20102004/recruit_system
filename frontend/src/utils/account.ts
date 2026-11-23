import type { UserDto } from "../api/client";

export function accountPath(user: UserDto): string {
  if (user.roleChosen === false) return "/choose-role";
  if (user.role === "RECRUITER" || user.role === "ADMIN") return "/recruiter";
  return "/candidate";
}
