import { useEffect, useRef } from "react";
import { GOOGLE_CLIENT_ID as CLIENT_ID } from "../../utils/google";

/**
 * Nút "Đăng nhập bằng Google" (Google Identity Services, specs/005-google-login).
 * Không có VITE_GOOGLE_CLIENT_ID thì không hiện gì.
 */
const GSI_SRC = "https://accounts.google.com/gsi/client";

interface GoogleId {
  initialize: (opts: { client_id: string; callback: (r: { credential: string }) => void; ux_mode?: string }) => void;
  renderButton: (el: HTMLElement, opts: Record<string, unknown>) => void;
}
type GoogleWindow = Window & { google?: { accounts?: { id?: GoogleId } } };

let loading: Promise<GoogleId> | null = null;

function loadGsi(): Promise<GoogleId> {
  if (loading) return loading;
  loading = new Promise((resolve, reject) => {
    const ready = () => {
      const id = (window as GoogleWindow).google?.accounts?.id;
      if (id) resolve(id);
      else reject(new Error("Google Identity Services không khả dụng"));
    };
    if ((window as GoogleWindow).google?.accounts?.id) return ready();
    const script = document.createElement("script");
    script.src = GSI_SRC;
    script.async = true;
    script.onload = ready;
    script.onerror = () => { loading = null; reject(new Error("Không tải được Google Sign-In")); };
    document.head.appendChild(script);
  });
  return loading;
}

export function GoogleSignInButton({
  onCredential,
  onError,
  text = "signin_with",
}: {
  onCredential: (credential: string) => void;
  onError?: (message: string) => void;
  /** signin_with | signup_with | continue_with */
  text?: "signin_with" | "signup_with" | "continue_with";
}) {
  const box = useRef<HTMLDivElement>(null);
  const callback = useRef(onCredential);
  useEffect(() => {
    callback.current = onCredential;
  }, [onCredential]);

  useEffect(() => {
    if (!CLIENT_ID) return;
    let cancelled = false;
    loadGsi()
      .then((id) => {
        if (cancelled || !box.current) return;
        id.initialize({ client_id: CLIENT_ID, callback: (r) => callback.current(r.credential) });
        id.renderButton(box.current, {
          theme: "outline", size: "large", text, shape: "rectangular", locale: "vi",
          width: Math.min(box.current.clientWidth || 400, 400),
        });
      })
      .catch((e: Error) => onError?.(e.message));
    return () => { cancelled = true; };
  }, [text, onError]);

  if (!CLIENT_ID) return null;
  return <div ref={box} style={{ display: "flex", justifyContent: "center", minHeight: 44 }} />;
}
