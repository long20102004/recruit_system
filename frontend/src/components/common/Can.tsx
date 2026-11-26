import type { ReactNode } from "react";
import { useAuth } from "../../context/AuthContext";
import type { PermissionRequirement } from "../../utils/permissions";

/** Chỉ hiện children khi user có quyền (specs/004-rbac). Backend vẫn là nơi chặn thật. */
export function Can({ perm, children, fallback = null }: { perm: PermissionRequirement; children: ReactNode; fallback?: ReactNode }) {
  const { can } = useAuth();
  return <>{can(perm) ? children : fallback}</>;
}
