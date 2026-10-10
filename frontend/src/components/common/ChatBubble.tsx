import type { ReactNode } from "react";
import { classNames } from "../../utils/format";

interface ChatProps {
  children: ReactNode;
  className?: string;
}

export function Chat({ children, className }: ChatProps) {
  return <div className={classNames("chat", className)}>{children}</div>;
}

interface ChatBubbleProps {
  role: "ai" | "user";
  meta?: ReactNode;
  children: ReactNode;
}

export function ChatBubble({ role, meta, children }: ChatBubbleProps) {
  return (
    <div className={classNames("bubble", role)}>
      {meta != null ? <div className="meta">{meta}</div> : null}
      {children}
    </div>
  );
}
