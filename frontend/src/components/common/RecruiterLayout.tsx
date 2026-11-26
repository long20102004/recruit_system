import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Brand } from "./Brand";
import { NavIcon } from "./NavIcon";
import { useAuth } from "../../context/AuthContext";
import { initials } from "../../utils/format";
import type { PermissionRequirement } from "../../utils/permissions";

/** Khung trang nhà tuyển dụng (design canvas: SideNav + app-main). */
export type RecruiterNavKey =
  | "home" | "jobs" | "candidates" | "matching" | "interviews" | "users" | "roles"
  // Màn dùng dữ liệu mẫu (src/api/mock), chờ nối API.
  | "interviewResults" | "cvSearch" | "company" | "team"
  | "adminHome" | "companies" | "adminJobs" | "templates" | "questions";

type Entry = { group: string } | { key: RecruiterNavKey; label: string; to: string; perm: PermissionRequirement };

/** Mục menu kèm quyền cần có; mục không đủ quyền bị ẩn (specs/004-rbac). */
const ENTRIES: Entry[] = [
  { key: "home", label: "Tổng quan", to: "/recruiter", perm: "dashboard:recruiter" },
  { group: "Tuyển dụng" },
  { key: "jobs", label: "Tin tuyển dụng", to: "/recruiter/jobs", perm: "job:read-own" },
  { key: "candidates", label: "Đơn ứng tuyển", to: "/recruiter/candidates", perm: "application:read-received" },
  { key: "matching", label: "Xếp hạng matching", to: "/recruiter/matching", perm: ["matching:run", "matching:read-all"] },
  { key: "interviewResults", label: "Kết quả phỏng vấn", to: "/recruiter/interview-results", perm: "job:read-own" },
  { key: "interviews", label: "Ngân hàng câu hỏi", to: "/recruiter/interviews", perm: "question:read" },
  { key: "cvSearch", label: "Tìm & lưu CV", to: "/recruiter/cv-search", perm: "job:read-own" },
  { group: "Công ty" },
  { key: "company", label: "Hồ sơ công ty", to: "/recruiter/company", perm: "job:read-own" },
  { key: "team", label: "Thành viên", to: "/recruiter/team", perm: "job:read-own" },
];

/** Menu khu quản trị (design canvas SideNav area="admin"). */
const ADMIN_ENTRIES: Entry[] = [
  { key: "adminHome", label: "Tổng quan", to: "/admin", perm: "user:read" },
  { key: "companies", label: "Duyệt công ty", to: "/admin/companies", perm: "user:read" },
  { key: "adminJobs", label: "Tin tuyển dụng", to: "/admin/jobs", perm: "user:read" },
  { key: "users", label: "Người dùng", to: "/admin/users", perm: "user:read" },
  { key: "questions", label: "Ngân hàng câu hỏi", to: "/admin/questions", perm: "user:read" },
  { key: "templates", label: "Mẫu CV", to: "/admin/cv-templates", perm: "user:read" },
  { key: "roles", label: "Phân quyền", to: "/admin/roles", perm: "role:manage" },
];

/** Bỏ mục không đủ quyền và tiêu đề nhóm không còn mục nào. */
function visibleEntries(entries: Entry[], can: (p: PermissionRequirement) => boolean): Entry[] {
  const out: Entry[] = [];
  for (const e of entries) {
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
          <Brand to={admin ? "/admin" : "/recruiter"} />
          <p className="sidenav-area"><span className="sn-label">{admin ? "Quản trị hệ thống" : "Nhà tuyển dụng"}</span></p>
          <nav aria-label="Điều hướng" style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {visibleEntries(admin ? ADMIN_ENTRIES : ENTRIES, can).map((e) =>
              "group" in e ? (
                <p key={e.group} className="sidenav-group"><span className="sn-label">{e.group}</span></p>
              ) : (
                <Link key={e.key} to={e.to} className={e.key === active ? "item on" : "item"} title={e.label}
                  aria-current={e.key === active ? "page" : undefined}>
                  <NavIcon name={e.key} />
                  <span className="sn-label">{e.label}</span>
                </Link>
              )
            )}
            <p className="sidenav-group"><span className="sn-label">Khác</span></p>
            <Link to="/jobs" className="item" title="Việc làm công khai">
              <NavIcon name="publicJobs" />
              <span className="sn-label">Việc làm công khai</span>
            </Link>
          </nav>
          <div className="sidenav-user">
            <span className="avatar">{initials(user?.fullName)}</span>
            <div className="sn-label" style={{ minWidth: 0, flex: 1 }}>
              <p style={{ fontSize: 13.5, fontWeight: 600, color: "#fbf8f3" }}>{user?.fullName}</p>
              <p style={{ fontSize: 12, color: "#bfb5a8", overflow: "hidden", textOverflow: "ellipsis" }}>{user?.email}</p>
              <button type="button" className="sidenav-logout"
                onClick={() => { logout(); navigate("/"); }}>
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
