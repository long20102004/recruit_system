import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
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
import {
  ApiError,
  AuthErrorCode,
  PASSWORD_HINT,
  PASSWORD_RULE,
  authApi,
} from "../api/client";

/** Trang đích của link đặt lại mật khẩu: /reset-password?token=… */
export function ResetPasswordPage() {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [invalidLink, setInvalidLink] = useState(!token);

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
      const res = await authApi.resetPassword(token, password);
      toast(res.message);
      navigate("/login", { replace: true });
    } catch (e) {
      if (e instanceof ApiError && e.code === AuthErrorCode.INVALID_LINK_TOKEN) {
        setInvalidLink(true);
      } else {
        toast(e instanceof ApiError ? e.message : "Không đặt lại được mật khẩu");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthPage>
      <AuthPanel>
        <AuthAside
          kicker="Bước 2 / 2 · mở từ email"
          title="Mật khẩu mới"
          description="Sau khi đổi, mọi phiên đăng nhập cũ trên các thiết bị khác sẽ bị đăng xuất."
        />
        {invalidLink ? (
          <AuthForm
            title="Link không hợp lệ"
            subtitle="Link đã được dùng hoặc đã hết hạn."
          >
            <Button variant="primary" block to="/forgot-password">
              Gửi lại link đặt lại mật khẩu
            </Button>
            <p className="small muted">
              <Link to="/login">Quay lại đăng nhập</Link>
            </p>
          </AuthForm>
        ) : (
          <AuthForm
            title="Đặt mật khẩu mới"
            subtitle={PASSWORD_HINT}
            onSubmit={onSubmit}
          >
            <Field label="Mật khẩu mới">
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
            <Field label="Nhập lại mật khẩu mới">
              <TextInput
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
                required
              />
            </Field>
            <Button variant="primary" block type="submit" disabled={busy}>
              {busy ? "Đang lưu…" : "Đặt mật khẩu"}
            </Button>
          </AuthForm>
        )}
      </AuthPanel>
    </AuthPage>
  );
}
