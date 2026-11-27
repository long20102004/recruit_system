import { useEffect, useRef, useState } from "react";

interface DocxPreviewProps {
  file: File;
  title?: string;
}

/** Xem trước file Word (.docx) trong phiên tải lên hiện tại bằng docx-preview (tải động). */
export function DocxPreview({ file, title }: DocxPreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const styleRef = useRef<HTMLDivElement>(null);
  const [result, setResult] = useState<{ file: File; state: "ready" | "error" } | null>(null);
  const status = result?.file === file ? result.state : "loading";

  useEffect(() => {
    let alive = true;

    (async () => {
      try {
        const buf = await file.arrayBuffer();
        const { renderAsync } = await import("docx-preview");
        if (!alive || !containerRef.current || !styleRef.current) return;
        containerRef.current.innerHTML = "";
        styleRef.current.innerHTML = "";
        await renderAsync(buf, containerRef.current, styleRef.current, {
          inWrapper: false,
          ignoreWidth: true,
          ignoreHeight: true,
          breakPages: false,
          useBase64URL: true,
        });
        if (alive) setResult({ file, state: "ready" });
      } catch {
        if (alive) setResult({ file, state: "error" });
      }
    })();

    return () => {
      alive = false;
    };
  }, [file]);

  return (
    <div className="cvu-docx" role="region" aria-label={title ?? "Xem trước CV Word"}>
      <div ref={styleRef} aria-hidden="true" />
      {status === "loading" ? <p className="cvu-help cvu-docx-msg">Đang tạo bản xem trước…</p> : null}
      {status === "error" ? (
        <p className="cvu-help cvu-docx-msg">Không hiển thị được bản xem trước file Word này.</p>
      ) : null}
      <div ref={containerRef} className="cvu-docx-body" hidden={status !== "ready"} />
    </div>
  );
}
