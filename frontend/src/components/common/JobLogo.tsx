import type { CSSProperties } from "react";
import { classNames } from "../../utils/format";

interface JobLogoProps {
  initials: string;
  color?: string;
  className?: string;
  style?: CSSProperties;
}

export function JobLogo({ initials, color, className, style }: JobLogoProps) {
  return (
    <div
      className={classNames("job-logo", className)}
      style={{ background: color, ...style }}
    >
      {initials}
    </div>
  );
}
