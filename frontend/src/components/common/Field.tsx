import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

interface FieldProps {
  label: ReactNode;
  htmlFor?: string;
  children: ReactNode;
  className?: string;
}

export function Field({ label, htmlFor, children, className }: FieldProps) {
  return (
    <div className={className ? `field ${className}` : "field"}>
      <label htmlFor={htmlFor}>{label}</label>
      {children}
    </div>
  );
}

type InputProps = InputHTMLAttributes<HTMLInputElement>;
type SelectProps = SelectHTMLAttributes<HTMLSelectElement>;
type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

export function TextInput({ className, ...props }: InputProps) {
  return <input className={className ? `input ${className}` : "input"} {...props} />;
}

export function TextSelect({ className, ...props }: SelectProps) {
  return <select className={className ? `input ${className}` : "input"} {...props} />;
}

export function TextTextarea({ className, ...props }: TextareaProps) {
  return <textarea className={className ? `input ${className}` : "input"} {...props} />;
}

interface HintProps {
  children: ReactNode;
  className?: string;
}

export function Hint({ children, className }: HintProps) {
  return <p className={className ? `help ${className}` : "help"}>{children}</p>;
}
