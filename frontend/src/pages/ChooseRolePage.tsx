import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import {
  AuthAside,
  AuthForm,
  AuthPage,
  AuthPanel,
  Button,
  RoleOption,
  RoleSwitch,
} from "../components/common";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { ApiError, type RoleDto } from "../api/client";
import { accountPath } from "../utils/account";

export function ChooseRolePage() {
  const { user, loading, chooseRole } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [role, setRole] = useState<Exclude<RoleDto, "ADMIN">>("CANDIDATE");
  const [busy, setBusy] = useState(false);

  if (loading) return <main className="page">Đang tải…</main>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.roleChosen !== false) return <Navigate to={accountPath(user)} replace />;

  async function onSubmit() {
    setBusy(true);
    try {
      const updated = await chooseRole(role);
      toast("Đã lưu vai trò");
      navigate(accountPath(updated));
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Không lưu được vai trò");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthPage>
      <AuthPanel>
        <AuthAside
          title="Bạn dùng hệ thống với vai trò nào?"
          description="Chọn một lần. Những lần đăng nhập sau sẽ mở đúng phần việc của vai trò này."
        />
        <AuthForm
          title="Chọn vai trò"
          subtitle="Ứng viên tìm việc và nộp CV. Nhà tuyển dụng đăng tin và xem hồ sơ."
          onSubmit={onSubmit}
        >
          <RoleSwitch aria-label="Chọn vai trò">
            <RoleOption
              title="Ứng viên"
              description="Tìm việc, nộp CV, xem việc phù hợp"
              active={role === "CANDIDATE"}
              onClick={() => setRole("CANDIDATE")}
            />
            <RoleOption
              title="Nhà tuyển dụng"
              description="Đăng tin và theo dõi ứng viên"
              active={role === "RECRUITER"}
              onClick={() => setRole("RECRUITER")}
            />
          </RoleSwitch>
          <Button variant="primary" block type="submit" disabled={busy}>
            {busy ? "Đang lưu…" : "Tiếp tục"}
          </Button>
        </AuthForm>
      </AuthPanel>
    </AuthPage>
  );
}
