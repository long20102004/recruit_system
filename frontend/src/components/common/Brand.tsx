import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import { classNames } from "../../utils/format";

interface BrandProps {
  to?: string;
  className?: string;
  style?: CSSProperties;
}

export function Brand({ to = "/", className, style }: BrandProps) {
  return (
    <Link className={classNames("brand-hl", className)} to={to} style={style}>
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#2f4cb8" strokeWidth="2" aria-hidden="true">
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="M15.5 15.5 21 21" />
        <path d="M8 10.5h5" />
      </svg>
      HireLens
    </Link>
  );
}
