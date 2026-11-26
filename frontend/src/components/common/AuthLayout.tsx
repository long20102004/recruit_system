import type { FormEvent, ReactNode } from "react";
import { Brand } from "./Brand";

/** Layout trang đăng nhập / đăng ký (design canvas: Login, Register): cột tối bên trái, form bên phải. */

export function AuthPage({ children }: { children: ReactNode }) {
  return <main className="auth-split">{children}</main>;
}

/** Giữ để tương thích; khung chia đôi nằm ở AuthPage. */
export function AuthPanel({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

interface AuthAsideProps {
  title: ReactNode;
  description: ReactNode;
  kicker?: ReactNode;
  points?: ReactNode[];
  footer?: ReactNode;
  brandTo?: string;
}

export function AuthAside({ title, description, kicker, points, footer, brandTo = "/" }: AuthAsideProps) {
  return (
    <section className="auth-split-aside">
      <Brand to={brandTo} />
      <div style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 460 }}>
        {kicker ? <p className="kicker" style={{ color: "#b8c5f0" }}>{kicker}</p> : null}
        <h1>{title}</h1>
        {points?.length ? (
          <ul>{points.map((p, i) => <li key={i}>{p}</li>)}</ul>
        ) : (
          <p>{description}</p>
        )}
      </div>
      <p className="small" style={{ color: "#a39888" }}>{footer ?? "© 2026 HireLens · PTIT"}</p>
    </section>
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
    <section className="auth-split-main">
      <form
        className="auth-split-form"
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit?.(e);
        }}
      >
        <div>
          <h2>{title}</h2>
          {subtitle != null ? <p className="muted" style={{ marginTop: 6 }}>{subtitle}</p> : null}
        </div>
        {children}
      </form>
    </section>
  );
}
