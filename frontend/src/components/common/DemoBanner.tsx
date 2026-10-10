import type { ReactNode } from "react";

interface DemoBannerProps {
  children: ReactNode;
}

/** Prototype demo notice strip — matches `.demo-banner`. */
export function DemoBanner({ children }: DemoBannerProps) {
  return <div className="demo-banner">{children}</div>;
}
