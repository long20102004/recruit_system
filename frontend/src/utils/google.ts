/** Client ID Google (VITE_GOOGLE_CLIENT_ID trong .env gốc repo); rỗng = tắt đăng nhập Google. */
export const GOOGLE_CLIENT_ID = (import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined)?.trim() ?? "";

export function isGoogleSignInEnabled(): boolean {
  return GOOGLE_CLIENT_ID.length > 0;
}
