import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Brand, Button } from "../components/common";
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

  if (loading) return <main className="wrap page-hl muted">Đang tải…</main>;
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

  const options: {
    value: Exclude<RoleDto, "ADMIN">;
    title: string;
    points: string[];
    icon: React.ReactNode;
  }[] = [
    {
      value: "CANDIDATE",
      title: "Tôi tìm việc",
      points: ["Tải CV, xem việc phù hợp", "Ứng tuyển và theo dõi đơn", "Luyện phỏng vấn theo JD"],
      icon: (
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
          <circle cx="12" cy="8" r="4" />
          <path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
        </svg>
      ),
    },
    {
      value: "RECRUITER",
      title: "Tôi tuyển dụng",
      points: ["Đăng tin, quản lý đơn ứng tuyển", "Xếp hạng ứng viên theo CV", "Xem kết quả phỏng vấn"],
      icon: (
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
          <rect x="3" y="7" width="18" height="13" rx="1" />
          <path d="M9 7V4h6v3" />
        </svg>
      ),
    },
  ];

  return (
    <div className="auth-simple">
      <header className="wrap" style={{ minHeight: 72, display: "flex", alignItems: "center" }}>
        <Brand to="/" />
      </header>
      <form
        className="wrap"
        style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
          gap: 28, paddingBottom: 64, textAlign: "center" }}
        onSubmit={(e) => {
          e.preventDefault();
          void onSubmit();
        }}
      >
        <div>
          <p className="kicker">Bước cuối · chỉ chọn một lần</p>
          <h1 style={{ fontSize: 40, marginTop: 8 }}>Bạn dùng HireLens để làm gì?</h1>
          <p className="muted" style={{ marginTop: 10 }}>
            Vai trò quyết định giao diện bạn thấy. Sau khi chọn sẽ không đổi được; cần đổi thì liên hệ quản trị viên.
          </p>
        </div>
        <div role="radiogroup" aria-label="Chọn vai trò"
          style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 340px), 1fr))", gap: 20,
            width: "min(780px, 100%)", textAlign: "left" }}>
          {options.map((o) => {
            const on = role === o.value;
            return (
              <label key={o.value} className="card"
                style={{ padding: 28, display: "flex", flexDirection: "column", gap: 14, cursor: "pointer",
                  border: on ? "2px solid var(--brand)" : undefined, background: on ? "#f5f7fd" : undefined }}>
                <div className="between">
                  <span className="logo" style={{ color: on ? "var(--brand)" : "var(--ink-soft)",
                    background: on ? "var(--brand-soft)" : undefined }}>{o.icon}</span>
                  <input type="radio" name="role" checked={on} onChange={() => setRole(o.value)}
                    style={{ width: 20, height: 20, accentColor: "var(--brand)" }} />
                </div>
                <h3>{o.title}</h3>
                <ul style={{ margin: 0, paddingLeft: 18, color: "var(--ink-soft)", display: "grid", gap: 4, fontSize: 14 }}>
                  {o.points.map((p) => <li key={p}>{p}</li>)}
                </ul>
              </label>
            );
          })}
        </div>
        <Button variant="primary" type="submit" disabled={busy} style={{ minWidth: 260 }}>
          {busy ? "Đang lưu…" : "Tiếp tục"}
        </Button>
      </form>
    </div>
  );
}
