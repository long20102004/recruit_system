import type { ReactNode } from "react";

interface StatProps {
  label: ReactNode;
  value: ReactNode;
  note?: ReactNode;
}

export function Stat({ label, value, note }: StatProps) {
  return (
    <article className="stat">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {note != null ? <div className="note">{note}</div> : null}
    </article>
  );
}
