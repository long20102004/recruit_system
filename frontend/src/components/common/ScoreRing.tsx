import type { CSSProperties, ReactNode } from "react";
import { classNames } from "../../utils/format";

interface ScoreRingProps {
  /** Progress 0–100 for conic gradient `--p`. */
  percent: number;
  children?: ReactNode;
  size?: number;
  innerSize?: number;
  fontSize?: string;
  className?: string;
}

export function ScoreRing({
  percent,
  children,
  size = 78,
  innerSize = 60,
  fontSize = "1.05rem",
  className,
}: ScoreRingProps) {
  const style = {
    "--p": percent,
    width: size,
    height: size,
  } as CSSProperties;

  return (
    <div className={classNames("score-ring", className)} style={style}>
      <span style={{ width: innerSize, height: innerSize, fontSize }}>
        {children}
      </span>
    </div>
  );
}
