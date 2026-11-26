import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { accountPath } from "../../utils/account";
import { isGoogleSignInEnabled } from "../../utils/google";
import { GoogleSignInButton } from "./GoogleSignInButton";

/**
 * "hoặc" + nút Google cho trang đăng nhập / đăng ký (specs/005-google-login).
 * Người dùng mới qua Google được chuyển tới màn chọn vai trò (accountPath).
 */
export function GoogleAuthBlock({ text = "signin_with" }: { text?: "signin_with" | "signup_with" }) {
  const { loginWithGoogle } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const onCredential = useCallback(async (credential: string) => {
    setError(null);
    try {
      const user = await loginWithGoogle(credential);
      toast("Đăng nhập bằng Google thành công");
      navigate(accountPath(user), { replace: true });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Không đăng nhập được bằng Google");
    }
  }, [loginWithGoogle, navigate, toast]);

  const onError = useCallback((m: string) => setError(m), []);

  if (!isGoogleSignInEnabled()) return null;
  return (
    <>
      <div className="row" style={{ gap: 12, flexWrap: "nowrap" }} aria-hidden="true">
        <span className="hr" style={{ flex: 1 }} />
        <span className="small muted">hoặc</span>
        <span className="hr" style={{ flex: 1 }} />
      </div>
      <GoogleSignInButton text={text} onCredential={onCredential} onError={onError} />
      {error ? <div className="note note-warn small" role="alert">{error}</div> : null}
    </>
  );
}
