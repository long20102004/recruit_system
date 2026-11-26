import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Brand } from "./Brand";
import { useAuth } from "../../context/AuthContext";
import { initials } from "../../utils/format";
import type { PermissionRequirement } from "../../utils/permissions";

/** Khung trang nhà tuyển dụng (design canvas: SideNav + app-main). */
export type RecruiterNavKey = "home" | "jobs" | "candidates" | "matching" | "interviews" | "users" | "roles";

type Entry = { group: string } | { key: RecruiterNavKey; label: string; to: string; perm: PermissionRequirement };

/** Mục menu kèm quyền cần có; mục không đủ quyền bị ẩn (specs/004-rbac). */
const ENTRIES: Entry[] = [
  { key: "home", label: "Tổng quan", to: "/recruiter", perm: "dashboard:recruiter" },
  { group: "Tuyển dụng" },
  { key: "jobs", label: "Tin tuyển dụng", to: "/recruiter/jobs", perm: "job:read-own" },
  { key: "candidates", label: "Đơn ứng tuyển", to: "/recruiter/candidates", perm: "application:read-received" },
  { key: "matching", label: "Xếp hạng matching", to: "/recruiter/matching", perm: ["matching:run", "matching:read-all"] },
  { key: "interviews", label: "Ngân hàng câu hỏi", to: "/recruiter/interviews", perm: "question:read" },
  { group: "Quản trị" },
  { key: "users", label: "Người dùng", to: "/admin/users", perm: "user:read" },
  { key: "roles", label: "Phân quyền", to: "/admin/roles", perm: "role:manage" },
];

/** Bỏ mục không đủ quyền và tiêu đề nhóm không còn mục nào. */
function visibleEntries(can: (p: PermissionRequirement) => boolean): Entry[] {
  const out: Entry[] = [];
  for (const e of ENTRIES) {
    if ("group" in e) out.push(e);
    else if (can(e.perm)) out.push(e);
  }
  return out.filter((e, i) => !("group" in e) || (i + 1 < out.length && !("group" in out[i + 1])));
}

export function RecruiterLayout({ active, children }: { active: RecruiterNavKey; children: ReactNode }) {
  const { user, logout, can } = useAuth();
  const navigate = useNavigate();
  const admin = user?.role === "ADMIN";

  return (
    <div className="app">
      <div className="app-side">
        <aside className="sidenav">
          <Brand to="/recruiter" />
          <p className="sidenav-area">{admin ? "Quản trị hệ thống" : "Nhà tuyển dụng"}</p>
          <nav aria-label="Điều hướng" style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {visibleEntries(can).map((e) =>
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
