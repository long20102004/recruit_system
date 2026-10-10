import type { FormEvent, ReactNode } from "react";
import { Brand } from "./Brand";

interface AuthPageProps {
  children: ReactNode;
}

export function AuthPage({ children }: AuthPageProps) {
  return <main className="auth-page">{children}</main>;
}

interface AuthPanelProps {
  children: ReactNode;
}

export function AuthPanel({ children }: AuthPanelProps) {
  return <div className="auth-panel">{children}</div>;
}

interface AuthAsideProps {
  title: ReactNode;
  description: ReactNode;
  footer?: ReactNode;
  brandTo?: string;
}

export function AuthAside({
  title,
  description,
  footer,
  brandTo = "/",
}: AuthAsideProps) {
  return (
    <aside className="auth-aside">
      <div>
        <Brand to={brandTo} style={{ color: "#fff" }} />
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {footer != null ? (
        <p style={{ fontSize: ".9rem", opacity: 0.85, margin: 0 }}>{footer}</p>
      ) : null}
    </aside>
  );
}

interface AuthFormProps {
  title: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  onSubmit?: (e: FormEvent<HTMLFormElement>) => void;
}

export function AuthForm({ title, subtitle, children, onSubmit }: AuthFormProps) {
  return (
    <form
      className="auth-form"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit?.(e);
      }}
    >
      <h2>{title}</h2>
      {subtitle != null ? <p className="muted">{subtitle}</p> : null}
      {children}
    </form>
  );
}
