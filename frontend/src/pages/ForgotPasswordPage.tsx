import { useState } from "react";
import { Link } from "react-router-dom";
import {
  AuthAside,
  AuthForm,
  AuthPage,
  AuthPanel,
  Button,
  Field,
  TextInput,
} from "../components/common";
import { useToast } from "../context/ToastContext";
import { ApiError, authApi } from "../api/client";

export function ForgotPasswordPage() {
  const { toast } = useToast();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState<string | null>(null);

  async function onSubmit() {
    setBusy(true);
    try {
      const res = await authApi.forgotPassword(email.trim());
      setSent(res.message);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Không gửi được yêu cầu");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthPage>
      <AuthPanel>
        <AuthAside
          title="Quên mật khẩu"
          description="Nhập email đã đăng ký, chúng tôi sẽ gửi link để bạn đặt mật khẩu mới."
        />
        {sent ? (
          <AuthForm title="Kiểm tra hộp thư" subtitle={sent}>
            <p className="hint">
              Link có hiệu lực 30 phút và chỉ dùng được một lần.
              <br />
              <Link to="/login">Quay lại đăng nhập</Link>
            </p>
          </AuthForm>
        ) : (
          <AuthForm
            title="Đặt lại mật khẩu"
            subtitle="Nhập email của tài khoản."
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
            <Button variant="primary" block type="submit" disabled={busy}>
              {busy ? "Đang gửi…" : "Gửi link đặt lại"}
            </Button>
            <p className="hint">
              <Link to="/login">Quay lại đăng nhập</Link>
            </p>
          </AuthForm>
        )}
      </AuthPanel>
    </AuthPage>
  );
}
