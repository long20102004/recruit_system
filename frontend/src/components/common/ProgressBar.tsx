import type { CSSProperties } from "react";

interface ProgressBarProps {
  /** Width percent 0–100. */
  percent: number;
  className?: string;
}

export function ProgressBar({ percent, className }: ProgressBarProps) {
  const style = { "--w": `${percent}%` } as CSSProperties;
  return (
    <div className={className ? `progress ${className}` : "progress"} style={style}>
      <i />
    </div>
  );
}
