import type { ReactNode } from "react";
import { classNames } from "../../utils/format";
import type { ChipTone } from "../../types";

interface ChipProps {
  children: ReactNode;
  tone?: ChipTone;
  className?: string;
}

export function Chip({ children, tone = "default", className }: ChipProps) {
  return (
    <span
      className={classNames(
        "chip",
        tone !== "default" && tone,
        className
      )}
    >
      {children}
    </span>
  );
}

interface ChipFilterProps {
  children: ReactNode;
  active?: boolean;
  onClick?: () => void;
  className?: string;
  type?: "button" | "submit";
}

export function ChipFilter({
  children,
  active,
  onClick,
  className,
  type = "button",
}: ChipFilterProps) {
  return (
    <button
      type={type}
      className={classNames("chip-filter", active && "active", className)}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
