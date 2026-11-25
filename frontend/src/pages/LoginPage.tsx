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
          title="Chào mừng trở lại"
          description="Đăng nhập để tiếp tục tìm việc, quản lý hồ sơ hoặc theo dõi tin tuyển dụng của bạn."
        />
        <AuthForm
          title="Đăng nhập"
          subtitle="Nhập email và mật khẩu của tài khoản đã đăng ký."
          onSubmit={onSubmit}
        >
          <Field label="Email">
            <TextInput
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </Field>
          <Field label="Mật khẩu">
            <TextInput
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </Field>

          {notice ? (
            <p className="hint" role="alert">
              {notice}
            </p>
          ) : null}
          <Button variant="primary" block type="submit" disabled={busy}>
            {busy ? "Đang vào…" : "Đăng nhập"}
          </Button>
          {unverifiedEmail ? <ResendVerificationButton email={unverifiedEmail} /> : null}
          <p className="hint">
            <Link to="/forgot-password">Quên mật khẩu?</Link>
            <br />
            Chưa có tài khoản? <Link to="/register">Đăng ký</Link>
            <br />
            <Link to="/">Quay lại danh sách việc làm</Link>
          </p>
        </AuthForm>
      </AuthPanel>
    </AuthPage>
  );
}
