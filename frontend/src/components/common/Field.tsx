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

export function TextInput(props: InputProps) {
  return <input {...props} />;
}

export function TextSelect(props: SelectProps) {
  return <select {...props} />;
}

export function TextTextarea(props: TextareaProps) {
  return <textarea {...props} />;
}

interface HintProps {
  children: ReactNode;
  className?: string;
}

export function Hint({ children, className }: HintProps) {
  return <p className={className ? `hint ${className}` : "hint"}>{children}</p>;
}
