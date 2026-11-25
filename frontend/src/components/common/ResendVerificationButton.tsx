import { useState } from "react";
import { ApiError, authApi } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { Button } from "./Button";

/** Gửi lại email xác thực; backend luôn trả cùng một thông báo và tự giãn cách 60 giây. */
export function ResendVerificationButton({ email }: { email: string }) {
  const { toast } = useToast();
  const [busy, setBusy] = useState(false);

  async function resend() {
    setBusy(true);
    try {
      const res = await authApi.resendVerification(email);
      toast(res.message);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Không gửi lại được email");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Button variant="ghost" block type="button" disabled={busy || !email} onClick={resend}>
      {busy ? "Đang gửi…" : "Gửi lại email xác thực"}
    </Button>
  );
}
