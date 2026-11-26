import type { ReactNode } from "react";

interface PageProps {
  children: ReactNode;
  className?: string;
}

export function Page({ children, className }: PageProps) {
  return (
    <main className={className ? `wrap page-hl ${className}` : "wrap page-hl"}>{children}</main>
  );
}

interface PageHeadProps {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}

export function PageHead({ title, description, actions }: PageHeadProps) {
  return (
    <header className="page-head">
      <div>
        <h1 style={{ fontSize: 32 }}>{title}</h1>
        {description ? <p className="muted">{description}</p> : null}
      </div>
      {actions}
    </header>
  );
}

interface SectionHeadProps {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}

export function SectionHead({ title, subtitle, actions }: SectionHeadProps) {
  return (
    <div className="between" style={{ marginBottom: 12 }}>
      <div>
        <h2 style={{ fontSize: 22 }}>{title}</h2>
        {subtitle ? <p className="small muted" style={{ marginTop: 4 }}>{subtitle}</p> : null}
      </div>
      {actions}
    </div>
  );
}
