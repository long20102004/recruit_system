import type { ReactNode } from "react";
import { classNames } from "../../utils/format";

interface RoleOptionProps {
  title: ReactNode;
  description: ReactNode;
  active?: boolean;
  onClick?: () => void;
}

export function RoleOption({
  title,
  description,
  active,
  onClick,
}: RoleOptionProps) {
  return (
    <button
      type="button"
      className={classNames("role-option", active && "active")}
      onClick={onClick}
    >
      <strong>{title}</strong>
      <small>{description}</small>
    </button>
  );
}

interface RoleSwitchProps {
  children: ReactNode;
  "aria-label"?: string;
}

export function RoleSwitch({
  children,
  "aria-label": ariaLabel = "Vai trò",
}: RoleSwitchProps) {
  return (
    <div className="role-switch" role="group" aria-label={ariaLabel}>
      {children}
    </div>
  );
}
