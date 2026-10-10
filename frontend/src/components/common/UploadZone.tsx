import { useRef, type DragEvent, type ReactNode } from "react";
import { classNames } from "../../utils/format";

interface UploadZoneProps {
  title?: ReactNode;
  hint?: ReactNode;
  accept?: string;
  onFile?: (file: File) => void;
  className?: string;
}

export function UploadZone({
  title = "Kéo thả CV PDF/DOCX vào đây",
  hint = "hoặc bấm để chọn file · tối đa 5MB (demo)",
  accept = ".pdf,.doc,.docx",
  onFile,
  className,
}: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (file) onFile?.(file);
  }

  function onDragOver(e: DragEvent) {
    e.preventDefault();
    e.currentTarget.classList.add("dragover");
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
      className={classNames("upload-zone", className)}
      tabIndex={0}
      role="button"
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
      }}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <strong>{title}</strong>
      <p className="muted">{hint}</p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        hidden
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}
