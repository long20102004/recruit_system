import type { ReactNode } from "react";
import { classNames } from "../../utils/format";

interface StepsProps {
  children: ReactNode;
  className?: string;
}

export function Steps({ children, className }: StepsProps) {
  return <div className={classNames("steps", className)}>{children}</div>;
}

interface StepProps {
  children: ReactNode;
  status?: "idle" | "active" | "done";
}

export function Step({ children, status = "idle" }: StepProps) {
  return (
    <div
      className={classNames(
        "step",
        status === "active" && "active",
        status === "done" && "done"
      )}
    >
      {children}
    </div>
  );
}
