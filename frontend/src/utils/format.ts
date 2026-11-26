/** Convert 0–1 score to integer percent (matches HireLens.pct). */
export function pct(n: number): number {
  return Math.round(Number(n) * 100);
}

export function classNames(
  ...parts: Array<string | false | null | undefined>
): string {
  return parts.filter(Boolean).join(" ");
}

/** Chữ viết tắt cho avatar: "Nguyễn Văn An" → "NA". */
export function initials(name: string | null | undefined): string {
  const parts = (name ?? "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const last = parts[parts.length - 1][0] ?? "";
  const first = parts.length > 1 ? parts[0][0] : "";
  return (first + last).toUpperCase();
}

/** Trạng thái đơn ứng tuyển → nhãn + class badge (design canvas: Tokens). */
export function applicationBadge(status: string | null | undefined): { label: string; cls: string } {
  switch ((status ?? "").toUpperCase()) {
    case "SUBMITTED": return { label: "Đã nộp", cls: "badge" };
    case "REVIEWING": return { label: "Đang xem xét", cls: "badge b-brand" };
    case "INTERVIEW": return { label: "Phỏng vấn", cls: "badge b-gold" };
    case "HIRED": return { label: "Trúng tuyển", cls: "badge b-ok" };
    case "REJECTED": return { label: "Từ chối", cls: "badge b-danger" };
    case "WITHDRAWN": return { label: "Đã rút", cls: "badge b-plain" };
    default: return { label: status ?? "—", cls: "badge" };
  }
}

/** "2026-11-24T08:00:00" → "24/11/2026". */
export function shortDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("vi-VN");
}

/** Trạng thái tin tuyển dụng → nhãn + class badge. */
export function jobBadge(status: string | null | undefined): { label: string; cls: string } {
  switch ((status ?? "").toUpperCase()) {
    case "DRAFT": return { label: "Nháp", cls: "badge" };
    case "PUBLISHED": return { label: "Đang đăng", cls: "badge b-ok" };
    case "CLOSED": return { label: "Đã đóng", cls: "badge b-plain" };
    case "EXPIRED": return { label: "Hết hạn", cls: "badge b-warn" };
    case "LOCKED": return { label: "Bị khoá", cls: "badge b-danger" };
    default: return { label: status ?? "—", cls: "badge" };
  }
}
