import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Brand } from "./Brand";
import { useAuth } from "../../context/AuthContext";
import { initials } from "../../utils/format";

/** Khung trang nhà tuyển dụng (design canvas: SideNav + app-main). */
export type RecruiterNavKey = "home" | "jobs" | "candidates" | "matching" | "interviews";

type Entry = { group: string } | { key: RecruiterNavKey; label: string; to: string };

const ENTRIES: Entry[] = [
  { key: "home", label: "Tổng quan", to: "/recruiter" },
  { group: "Tuyển dụng" },
  { key: "jobs", label: "Tin tuyển dụng", to: "/recruiter/jobs" },
  { key: "candidates", label: "Đơn ứng tuyển", to: "/recruiter/candidates" },
  { key: "matching", label: "Xếp hạng matching", to: "/recruiter/matching" },
  { key: "interviews", label: "Kết quả phỏng vấn", to: "/recruiter/interviews" },
];

export function RecruiterLayout({ active, children }: { active: RecruiterNavKey; children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const admin = user?.role === "ADMIN";

  return (
    <div className="app">
      <div className="app-side">
        <aside className="sidenav">
          <Brand to="/recruiter" />
          <p className="sidenav-area">{admin ? "Quản trị hệ thống" : "Nhà tuyển dụng"}</p>
          <nav aria-label="Điều hướng" style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {ENTRIES.map((e) =>
              "group" in e ? (
                <p key={e.group} className="sidenav-group">{e.group}</p>
              ) : (
                <Link key={e.key} to={e.to} className={e.key === active ? "item on" : "item"}
                  aria-current={e.key === active ? "page" : undefined}>
                  <span>{e.label}</span>
                </Link>
              )
            )}
            <p className="sidenav-group">Khác</p>
            <Link to="/jobs" className="item"><span>Việc làm công khai</span></Link>
          </nav>
          <div className="sidenav-user">
            <span className="avatar">{initials(user?.fullName)}</span>
            <div style={{ minWidth: 0, flex: 1 }}>
              <p style={{ fontSize: 13.5, fontWeight: 600, color: "#fbf8f3" }}>{user?.fullName}</p>
              <p style={{ fontSize: 12, color: "#bfb5a8", overflow: "hidden", textOverflow: "ellipsis" }}>{user?.email}</p>
              <button type="button" className="sidenav-logout"
                onClick={() => { logout(); navigate("/login"); }}>
                Đăng xuất
              </button>
            </div>
          </div>
        </aside>
      </div>
      <main className="app-main" style={{ display: "flex", flexDirection: "column", gap: 24 }}>{children}</main>
    </div>
  );
}
