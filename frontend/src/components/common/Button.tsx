import type {
  ButtonHTMLAttributes,
  CSSProperties,
  ReactNode,
} from "react";
import { Link } from "react-router-dom";
import { classNames } from "../../utils/format";
import type { ButtonVariant } from "../../types";

type CommonProps = ButtonVariant & {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
};

type ButtonAsButton = CommonProps &
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className" | "style" | "children"> & {
    to?: undefined;
  };

type ButtonAsLink = CommonProps & {
  to: string;
  type?: never;
  onClick?: React.MouseEventHandler<HTMLAnchorElement>;
  disabled?: boolean;
};

export type ButtonProps = ButtonAsButton | ButtonAsLink;

function buttonClassName({
  variant = "primary",
  size = "md",
  block,
  className,
}: Pick<CommonProps, "variant" | "size" | "block" | "className">) {
  return classNames(
    "btn",
    variant === "primary" && "btn-primary",
    variant === "accent" && "btn-accent",
    variant === "ghost" && "btn-ghost",
    variant === "soft" && "btn-soft",
    size === "sm" && "btn-sm",
    block && "btn-block",
    className
  );
}

export function Button(props: ButtonProps) {
  const { children, variant, size, block, className, style } = props;
  const cls = buttonClassName({ variant, size, block, className });

  if ("to" in props && props.to) {
    const { to, onClick } = props;
    return (
      <Link className={cls} to={to} onClick={onClick} style={style}>
        {children}
      </Link>
    );
  }

  const buttonProps = props as ButtonAsButton;
  const { type = "button", to: _to, ...rest } = buttonProps;
  return (
    <button className={cls} type={type} style={style} {...rest}>
      {children}
    </button>
  );
}
