import { useId, type CSSProperties } from "react";
import { Link } from "react-router-dom";
import { classNames } from "../../utils/format";

interface BrandProps {
  to?: string;
  className?: string;
  style?: CSSProperties;
}

/** Huy hiệu HL (public/brand/mark.svg) vẽ inline; id gradient riêng cho mỗi lần render. */
export function BrandMark({ size = 30 }: { size?: number }) {
  const gid = useId();
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" style={{ flex: "none" }}>
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#4f74e3" />
          <stop offset="1" stopColor="#243a92" />
        </linearGradient>
      </defs>
      <circle cx="28" cy="28" r="26.5" fill={`url(#${gid})`} />
      <g fill="#fff" transform="translate(28 28) scale(0.94) translate(-31 -30)">
        <rect x="13" y="17" width="6.5" height="26" rx="1" />
        <rect x="25.5" y="17" width="6.5" height="26" rx="1" />
        <rect x="13" y="27" width="19" height="6" rx="1" />
        <rect x="35.5" y="17" width="6.5" height="26" rx="1" />
        <rect x="35.5" y="37" width="13.5" height="6" rx="1" />
      </g>
      <path d="M40 36.5v19l4.7-4.5 3.4 7.6 3.9-1.8-3.4-7.5h6.4z" fill="#1c2230" stroke="#fff" strokeWidth="2.2"
        strokeLinejoin="round" />
    </svg>
  );
}

export function Brand({ to = "/", className, style }: BrandProps) {
  return (
    <Link className={classNames("brand-hl", className)} to={to} style={style} aria-label="HireLens – trang chủ">
      <BrandMark />
      <span className="brand-text">Hire<span className="brand-accent">Lens</span></span>
    </Link>
  );
}
