import type { ReactNode } from "react";

interface StatProps {
  label: ReactNode;
  value: ReactNode;
  note?: ReactNode;
}

export function Stat({ label, value, note }: StatProps) {
  return (
    <div className="stat">
      <p className="l">{label}</p>
      <p className="v">{value}</p>
      {note != null ? <p className="help">{note}</p> : null}
    </div>
  );
}
