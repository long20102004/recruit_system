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
    <Link className={classNames("brand", className)} to={to} style={style}>
      <span className="brand-mark" aria-hidden="true" />
      HireLens
    </Link>
  );
}
