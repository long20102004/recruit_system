import type { ReactNode } from "react";
import { JobLogo } from "./JobLogo";

interface CompanyRowProps {
  logo: string;
  logoColor?: string;
  title: ReactNode;
  meta?: ReactNode;
}

export function CompanyRow({ logo, logoColor, title, meta }: CompanyRowProps) {
  return (
    <div className="company-row">
      <JobLogo initials={logo} color={logoColor} />
      <div>
        <h3 style={{ margin: "0 0 .2rem" }}>{title}</h3>
        {meta != null ? <div className="muted">{meta}</div> : null}
      </div>
    </div>
  );
}
