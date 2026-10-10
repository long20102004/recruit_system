import type { ReactNode } from "react";
import { classNames } from "../../utils/format";

interface BoxProps {
  children: ReactNode;
  className?: string;
}

export function LayoutFeed({ children, className }: BoxProps) {
  return (
    <div className={classNames("layout-feed", className)}>{children}</div>
  );
}

export function Grid2({ children, className }: BoxProps) {
  return <div className={classNames("grid-2", className)}>{children}</div>;
}

export function Grid3({ children, className }: BoxProps) {
  return <div className={classNames("grid-3", className)}>{children}</div>;
}

export function SplitActions({ children, className }: BoxProps) {
  return (
    <div className={classNames("split-actions", className)}>{children}</div>
  );
}

export function JobList({ children, className }: BoxProps) {
  return <div className={classNames("job-list", className)}>{children}</div>;
}

export function FilterChips({ children, className }: BoxProps) {
  return (
    <div className={classNames("filter-chips", className)}>{children}</div>
  );
}

export function Muted({ children, className }: BoxProps) {
  return <span className={classNames("muted", className)}>{children}</span>;
}

export function Kicker({ children, className }: BoxProps) {
  return <p className={classNames("kicker", className)}>{children}</p>;
}
