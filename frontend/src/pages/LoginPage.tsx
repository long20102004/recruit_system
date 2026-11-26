import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import {
  AuthAside,
  AuthForm,
  AuthPage,
  AuthPanel,
  Button,
  Field,
  ResendVerificationButton,
  TextInput,
} from "../components/common";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { ApiError, AuthErrorCode } from "../api/client";
import { accountPath } from "../utils/account";

export function LoginPage() {
  const { login, user, loading } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  /** Thông báo lỗi cần hiển thị lâu hơn toast (khoá tạm, bị khoá, chưa xác thực). */
  const [notice, setNotice] = useState<string | null>(null);
  const [unverifiedEmail, setUnverifiedEmail] = useState<string | null>(null);

  if (!loading && user) {
    return <Navigate to={accountPath(user)} replace />;
  }

  async function onSubmit() {
    setBusy(true);
    setNotice(null);
    setUnverifiedEmail(null);
    try {
      const signedIn = await login(email, password);
      toast("Đăng nhập thành công");
      navigate(accountPath(signedIn));
    } catch (e) {
      if (!(e instanceof ApiError)) {
        toast("Đăng nhập thất bại");
      } else if (e.code === AuthErrorCode.EMAIL_NOT_VERIFIED) {
        setNotice(e.message);
        setUnverifiedEmail(email.trim());
      } else if (
        e.code === AuthErrorCode.LOGIN_TEMPORARILY_LOCKED ||
        e.code === AuthErrorCode.ACCOUNT_LOCKED
      ) {
        setNotice(e.message);
      } else {
        toast(e.message);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthPage>
      <AuthPanel>
        <AuthAside
          kicker="Tuyển dụng IT có AI hỗ trợ"
          title="Một tài khoản cho cả tìm việc và tuyển dụng."
          description=""
          points={[
            "CV PDF được đọc và điền sẵn vào hồ sơ.",
            "Điểm phù hợp với từng tin tuyển dụng.",
            "Luyện phỏng vấn, chấm điểm từng câu trả lời.",
          ]}
        />
        <AuthForm title="Đăng nhập" subtitle="Chào mừng bạn quay lại." onSubmit={onSubmit}>
          <Field label="Email">
            <TextInput
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </Field>
          <div className="field">
            <div className="between">
              <label htmlFor="login-password" className="lbl">Mật khẩu</label>
              <Link to="/forgot-password" className="small" style={{ color: "var(--brand)", fontWeight: 600 }}>
                Quên mật khẩu?
              </Link>
            </div>
            <TextInput
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {notice ? (
            <div className="note note-warn small" role="alert">
              {notice}
            </div>
          ) : null}
          <Button variant="primary" block type="submit" disabled={busy}>
            {busy ? "Đang vào…" : "Đăng nhập"}
          </Button>
          {unverifiedEmail ? <ResendVerificationButton email={unverifiedEmail} /> : null}
          <p className="small muted" style={{ textAlign: "center" }}>
            Chưa có tài khoản?{" "}
            <Link to="/register" style={{ color: "var(--brand)", fontWeight: 650 }}>Đăng ký</Link>
            {" · "}
            <Link to="/">Xem việc làm</Link>
          </p>
        </AuthForm>
      </AuthPanel>
    </AuthPage>
  );
}
