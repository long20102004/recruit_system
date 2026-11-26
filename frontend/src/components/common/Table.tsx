import type { ReactNode, TableHTMLAttributes } from "react";
import { classNames } from "../../utils/format";

interface TableProps extends TableHTMLAttributes<HTMLTableElement> {
  children: ReactNode;
}

export function Table({ children, className, ...rest }: TableProps) {
  return (
    <div className="tbl-box">
      <table className={classNames("tbl", className)} {...rest}>
        {children}
      </table>
    </div>
  );
}
