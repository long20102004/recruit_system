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

export function RegisterPage() {
  const { register, user, loading } = useAuth();
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
      const created = await register({ email, password });
      toast("Tạo tài khoản thành công");
      navigate(accountPath(created));
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Không tạo được tài khoản");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthPage>
      <AuthPanel>
        <AuthAside
          title="Tạo tài khoản"
          description="Chỉ cần email và mật khẩu. Sau khi vào tài khoản lần đầu, bạn chọn dùng với vai trò ứng viên hoặc nhà tuyển dụng."
        />
        <AuthForm
          title="Đăng ký"
          subtitle="Email và mật khẩu dùng để đăng nhập những lần sau."
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
              autoComplete="new-password"
              minLength={6}
              required
            />
          </Field>

          <Button variant="primary" block type="submit" disabled={busy}>
            {busy ? "Đang tạo…" : "Tạo tài khoản"}
          </Button>
          <p className="hint">
            Đã có tài khoản? <Link to="/login">Đăng nhập</Link>
            <br />
            <Link to="/">Quay lại danh sách việc làm</Link>
          </p>
        </AuthForm>
      </AuthPanel>
    </AuthPage>
  );
}
