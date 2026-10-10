import type { ReactNode } from "react";

interface HeroSearchProps {
  kicker?: ReactNode;
  title: ReactNode;
  lead?: ReactNode;
  children?: ReactNode;
}

export function HeroSearch({ kicker, title, lead, children }: HeroSearchProps) {
  return (
    <section className="hero-search">
      {kicker != null ? <p className="kicker">{kicker}</p> : null}
      <h1>{title}</h1>
      {lead != null ? <p className="lead">{lead}</p> : null}
      {children}
    </section>
  );
}
