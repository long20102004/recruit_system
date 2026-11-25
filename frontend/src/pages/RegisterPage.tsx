import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
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
import { ApiError, PASSWORD_HINT, PASSWORD_RULE } from "../api/client";
import { accountPath } from "../utils/account";

export function RegisterPage() {
  const { register, user, loading } = useAuth();
  const { toast } = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  /** Email đã đăng ký, chờ người dùng bấm link xác thực. */
  const [sentTo, setSentTo] = useState<string | null>(null);

  if (!loading && user) {
    return <Navigate to={accountPath(user)} replace />;
  }

  async function onSubmit() {
    if (!PASSWORD_RULE.test(password)) {
      toast(PASSWORD_HINT);
      return;
    }
    if (password !== confirm) {
      toast("Mật khẩu nhập lại không khớp");
      return;
    }
    setBusy(true);
    try {
      const res = await register({ email, password });
      setSentTo(res.email);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Không tạo được tài khoản");
    } finally {
      setBusy(false);
    }
  }

  if (sentTo) {
    return (
      <AuthPage>
        <AuthPanel>
          <AuthAside
            title="Kiểm tra hộp thư"
            description="Tài khoản chỉ đăng nhập được sau khi bạn xác thực email."
          />
          <AuthForm
            title="Xác thực email"
            subtitle={
              <>
                Đã gửi link xác thực tới <strong>{sentTo}</strong>. Bấm vào link
                trong email để kích hoạt tài khoản. Link có hiệu lực 24 giờ.
              </>
            }
          >
            <ResendVerificationButton email={sentTo} />
            <p className="hint">
              Không thấy email? Kiểm tra thư mục spam rồi gửi lại.
              <br />
              <Link to="/login">Đến trang đăng nhập</Link>
            </p>
          </AuthForm>
        </AuthPanel>
      </AuthPage>
    );
  }

  return (
    <AuthPage>
      <AuthPanel>
        <AuthAside
          title="Tạo tài khoản"
          description="Chỉ cần email và mật khẩu. Sau khi xác thực email, bạn chọn dùng với vai trò ứng viên hoặc nhà tuyển dụng."
        />
        <AuthForm
          title="Đăng ký"
          subtitle="Chúng tôi sẽ gửi link xác thực tới email này."
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
              minLength={8}
              maxLength={100}
              required
            />
          </Field>
          <Field label="Nhập lại mật khẩu">
            <TextInput
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
              required
            />
          </Field>
          <p className="hint">{PASSWORD_HINT}</p>

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
