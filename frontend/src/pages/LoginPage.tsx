import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import {
  AuthAside,
  AuthForm,
  AuthPage,
  AuthPanel,
  Button,
  Field,
  TextInput,
} from "../components/common";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { ApiError } from "../api/client";
import { accountPath } from "../utils/account";

export function LoginPage() {
  const { login, user, loading } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  if (!loading && user) {
    return <Navigate to={accountPath(user)} replace />;
  }

  async function onSubmit() {
    setBusy(true);
    try {
      const signedIn = await login(email, password);
      toast("Đăng nhập thành công");
      navigate(accountPath(signedIn));
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Đăng nhập thất bại");
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

          <Button variant="primary" block type="submit" disabled={busy}>
            {busy ? "Đang vào…" : "Đăng nhập"}
          </Button>
          <p className="hint">
            Chưa có tài khoản? <Link to="/register">Đăng ký</Link>
            <br />
            <Link to="/">Quay lại danh sách việc làm</Link>
          </p>
        </AuthForm>
      </AuthPanel>
    </AuthPage>
  );
}
