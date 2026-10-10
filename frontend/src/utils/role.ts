import type { UserRole } from "../types";

const ROLE_KEY = "hirelens_role";

export function getRole(): UserRole {
  const stored = localStorage.getItem(ROLE_KEY);
  return stored === "recruiter" ? "recruiter" : "candidate";
}

export function setRole(role: UserRole): void {
  localStorage.setItem(ROLE_KEY, role);
}
