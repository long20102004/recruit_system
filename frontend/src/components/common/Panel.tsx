import type { HTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";
import { classNames } from "../../utils/format";

interface PanelProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode;
  as?: "article" | "section" | "aside" | "div";
}

export function Panel({
  children,
  as: Tag = "article",
  className,
  ...rest
}: PanelProps) {
  return (
    <Tag className={classNames("panel", className)} {...rest}>
      {children}
    </Tag>
  );
}

interface SidePanelProps {
  children: ReactNode;
  className?: string;
}

export function SidePanel({ children, className }: SidePanelProps) {
  return (
    <aside className={classNames("side-panel", className)}>{children}</aside>
  );
}

interface EmptyNoteProps {
  children: ReactNode;
  className?: string;
}

export function EmptyNote({ children, className }: EmptyNoteProps) {
  return (
    <div className={classNames("empty-note", className)}>{children}</div>
  );
}

interface QuickLinkProps {
  to: string;
  label: ReactNode;
  meta?: ReactNode;
}

export function QuickLink({ to, label, meta }: QuickLinkProps) {
  return (
    <Link className="quick-link" to={to}>
      {label}
      {meta != null ? <span>{meta}</span> : null}
    </Link>
  );
}
