import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  AuthAside,
  AuthForm,
  AuthPage,
  AuthPanel,
  Field,
  ResendVerificationButton,
  TextInput,
} from "../components/common";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { ApiError } from "../api/client";
import { accountPath } from "../utils/account";

/** Trang đích của link xác thực email: /verify-email?token=… */
export function VerifyEmailPage() {
  const { verifyEmail } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [error, setError] = useState<string | null>(
    token ? null : "Link xác thực không hợp lệ."
  );
  const [email, setEmail] = useState("");
  /** Token chỉ dùng được một lần; chặn StrictMode gọi hai lần. */
  const started = useRef(false);

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;
    verifyEmail(token)
      .then((user) => {
        toast("Đã xác thực email");
        navigate(accountPath(user), { replace: true });
      })
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Không xác thực được email")
      );
  }, [token, verifyEmail, navigate, toast]);

  return (
    <AuthPage>
      <AuthPanel>
        <AuthAside
          title="Xác thực email"
          description="Bước cuối trước khi bạn chọn vai trò và bắt đầu dùng HireLens."
        />
        {error == null ? (
          <AuthForm title="Đang xác thực…" subtitle="Vui lòng chờ trong giây lát.">
            {null}
          </AuthForm>
        ) : (
          <AuthForm
            title="Không xác thực được"
            subtitle={`${error} Nhập email để nhận link mới.`}
          >
            <Field label="Email">
              <TextInput
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </Field>
            <ResendVerificationButton email={email.trim()} />
            <p className="hint">
              <Link to="/login">Đến trang đăng nhập</Link>
            </p>
          </AuthForm>
        )}
      </AuthPanel>
    </AuthPage>
  );
}
