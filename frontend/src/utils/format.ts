/** Convert 0–1 score to integer percent (matches HireLens.pct). */
export function pct(n: number): number {
  return Math.round(Number(n) * 100);
}

export function classNames(
  ...parts: Array<string | false | null | undefined>
): string {
  return parts.filter(Boolean).join(" ");
}
