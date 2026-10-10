import type { ReactNode } from "react";

interface KvProps {
  children: ReactNode;
  className?: string;
}

export function Kv({ children, className }: KvProps) {
  return <div className={className ? `kv ${className}` : "kv"}>{children}</div>;
}

interface KvRowProps {
  label: ReactNode;
  children: ReactNode;
}

export function KvRow({ label, children }: KvRowProps) {
  return (
    <div className="kv-row">
      <label>{label}</label>
      <div>{children}</div>
    </div>
  );
}
