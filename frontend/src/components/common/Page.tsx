import type { ReactNode } from "react";

interface PageProps {
  children: ReactNode;
  className?: string;
}

export function Page({ children, className }: PageProps) {
  return (
    <main className={className ? `page ${className}` : "page"}>{children}</main>
  );
}

interface PageHeadProps {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}

export function PageHead({ title, description, actions }: PageHeadProps) {
  if (actions) {
    return (
      <header className="page-head">
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "space-between",
            gap: "1rem",
            alignItems: "end",
          }}
        >
          <div>
            <h1>{title}</h1>
            {description ? <p>{description}</p> : null}
          </div>
          {actions}
        </div>
      </header>
    );
  }

  return (
    <header className="page-head">
      <h1>{title}</h1>
      {description ? <p>{description}</p> : null}
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
    <div className="section-head">
      <div>
        <h2>{title}</h2>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      {actions}
    </div>
  );
}
