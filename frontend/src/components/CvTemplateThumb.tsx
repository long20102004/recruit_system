import type { CvTemplateConfig, CvTemplateType } from "../api/client";

/**
 * Hiển thị ảnh thu nhỏ mẫu CV (thumbnail từ R2 hoặc khung minh hoạ cấu hình/Word).
 */
export function CvTemplateThumb({
  name,
  type,
  config,
  thumbnailUrl,
  height = 180,
}: {
  name: string;
  type: CvTemplateType;
  config?: CvTemplateConfig | null;
  thumbnailUrl?: string | null;
  height?: number;
}) {
  if (thumbnailUrl) {
    return (
      <div
        style={{
          height,
          border: "1px solid var(--line)",
          background: "#fff",
          overflow: "hidden",
          display: "grid",
          placeItems: "center",
        }}
      >
        <img
          src={thumbnailUrl}
          alt={`Ảnh thu nhỏ mẫu ${name}`}
          style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
        />
      </div>
    );
  }

  if (type === "DOCX") {
    return (
      <div
        aria-hidden="true"
        style={{
          height,
          padding: 16,
          border: "1px solid var(--line)",
          background: "var(--sky)",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <div className="between">
          <span className="badge b-brand">Word (.docx)</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ height: 10, width: "60%", background: "var(--brand)", opacity: 0.5 }} />
          <div style={{ height: 6, width: "90%", background: "var(--ink-soft)", opacity: 0.22 }} />
          <div style={{ height: 6, width: "80%", background: "var(--ink-soft)", opacity: 0.22 }} />
          <div style={{ height: 6, width: "70%", background: "var(--ink-soft)", opacity: 0.18 }} />
        </div>
      </div>
    );
  }

  const bg = config?.background || "var(--paper)";
  const accent = config?.accent || "var(--brand)";
  const twoCol = config?.layout === "TWO_COLUMN";
  const centered = config?.header === "CENTER";

  return (
    <div
      aria-hidden="true"
      style={{
        height,
        padding: 14,
        border: "1px solid var(--line)",
        background: bg,
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: centered ? "center" : "flex-start",
          gap: 4,
        }}
      >
        <div style={{ height: 10, width: "55%", background: accent, opacity: 0.85 }} />
        <div style={{ height: 6, width: "38%", background: "var(--ink-soft)", opacity: 0.35 }} />
      </div>
      <div style={{ height: 1, background: accent, opacity: 0.35, margin: "4px 0" }} />
      {twoCol ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.6fr", gap: 8, flex: 1 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            <div style={{ height: 5, width: "85%", background: "var(--ink-soft)", opacity: 0.25 }} />
            <div style={{ height: 5, width: "70%", background: "var(--ink-soft)", opacity: 0.2 }} />
            <div style={{ height: 5, width: "90%", background: "var(--ink-soft)", opacity: 0.2 }} />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            <div style={{ height: 5, width: "95%", background: "var(--ink-soft)", opacity: 0.25 }} />
            <div style={{ height: 5, width: "85%", background: "var(--ink-soft)", opacity: 0.2 }} />
            <div style={{ height: 5, width: "90%", background: "var(--ink-soft)", opacity: 0.2 }} />
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
          <div style={{ height: 5, width: "90%", background: "var(--ink-soft)", opacity: 0.22 }} />
          <div style={{ height: 5, width: "82%", background: "var(--ink-soft)", opacity: 0.22 }} />
          <div style={{ height: 5, width: "86%", background: "var(--ink-soft)", opacity: 0.22 }} />
          <div style={{ height: 5, width: "68%", background: "var(--ink-soft)", opacity: 0.18 }} />
        </div>
      )}
    </div>
  );
}
