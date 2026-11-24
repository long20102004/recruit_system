import { useRef, type DragEvent, type ReactNode } from "react";
import { classNames } from "../../utils/format";

interface UploadZoneProps {
  title?: ReactNode;
  hint?: ReactNode;
  accept?: string;
  onFile?: (file: File) => void;
  className?: string;
  /** Khoá vùng tải (vd đang xử lý file trước): không mở hộp chọn, bỏ qua kéo thả. */
  disabled?: boolean;
  children?: ReactNode;
}

export function UploadZone({
  title = "Kéo thả CV PDF vào đây",
  hint = "Chỉ nhận file PDF · tối đa 10 MB",
  accept = ".pdf",
  onFile,
  className,
  disabled = false,
  children,
}: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  function open() {
    if (!disabled) inputRef.current?.click();
  }

  function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (file && !disabled) onFile?.(file);
  }

  function onDragOver(e: DragEvent) {
    e.preventDefault();
    if (!disabled) e.currentTarget.classList.add("dragover");
  }

  function onDragLeave(e: DragEvent) {
    e.currentTarget.classList.remove("dragover");
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    e.currentTarget.classList.remove("dragover");
    handleFiles(e.dataTransfer.files);
  }

  return (
    <div
      className={classNames("upload-zone", disabled && "disabled", className)}
      tabIndex={disabled ? -1 : 0}
      role="button"
      aria-disabled={disabled}
      onClick={open}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          open();
        }
      }}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <strong>{title}</strong>
      <p className="muted">{hint}</p>
      {children}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        hidden
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
