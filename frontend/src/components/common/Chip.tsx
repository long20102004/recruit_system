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
        tone === "hot" ? "badge b-hot" : tone === "ok" ? "badge b-ok b-plain" : tone === "warn" ? "badge b-warn b-plain" : "tag",
        (tone === "brand" || tone === "accent" || tone === "near") && "tag-on",
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
      className={classNames("tag", active && "tag-on", className)}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
