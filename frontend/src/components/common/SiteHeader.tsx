import { Link, useNavigate } from "react-router-dom";
import type { HeaderMode, NavKey } from "../../types";
import { Brand } from "./Brand";
import { NotificationBell } from "./NotificationBell";
import { useAuth } from "../../context/AuthContext";
import { accountPath } from "../../utils/account";
import { initials } from "../../utils/format";

/** Thanh điều hướng trên (design canvas: TopNav) cho khách và ứng viên. Recruiter dùng RecruiterLayout. */
export interface SiteHeaderProps {
  active: NavKey;
  mode: HeaderMode;
  userLocation?: string;
}

interface NavItem {
  to: string;
  key: NavKey;
  label: string;
}

const PUBLIC_LINKS: NavItem[] = [
  { to: "/jobs", key: "jobs", label: "Việc làm IT" },
  { to: "/companies", key: "companies", label: "Công ty" },
];

const CANDIDATE_LINKS: NavItem[] = [
  { to: "/candidate", key: "home", label: "Tổng quan" },
  { to: "/candidate/matching", key: "matching", label: "Việc phù hợp" },
  { to: "/candidate/cvs", key: "cv", label: "CV của tôi" },
  { to: "/candidate/applications", key: "applications", label: "Đơn ứng tuyển" },
  { to: "/candidate/interview", key: "interview", label: "Phỏng vấn" },
  { to: "/companies", key: "companies", label: "Công ty" },
];

export function SiteHeader({ active, mode, userLocation }: SiteHeaderProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const candidate = mode !== "public";
  const links = candidate ? CANDIDATE_LINKS : PUBLIC_LINKS;
  const streamEnabled = candidate && !!user;

  function onLogout() {
    logout();
    navigate("/");
  }

  return (
    <header className="topnav">
      <div className="wrap topnav-inner">
        <Brand to={candidate ? "/candidate" : "/"} />
        <nav aria-label="Chính" className="topnav-links">
          {links.map((l) => (
            <Link key={l.key} to={l.to} className={active === l.key ? "on" : undefined}
              aria-current={active === l.key ? "page" : undefined}>
              {l.label}
            </Link>
          ))}
        </nav>
        {userLocation ? <span className="tag">{userLocation}</span> : null}
        {!candidate ? (
          user ? (
            <Link to={accountPath(user)} className="btn btn-p btn-sm">Trang của tôi</Link>
          ) : (
            <div className="row" style={{ gap: 8 }}>
              <Link to="/login" className="btn btn-sm" style={{ fontWeight: 600 }}>Đăng nhập</Link>
              <Link to="/register" className="btn btn-g btn-sm">Đăng ký</Link>
              <span className="topnav-sep" />
              <Link to="/register" className="btn btn-sm" style={{ color: "var(--brand)" }}>Nhà tuyển dụng</Link>
            </div>
          )
        ) : (
          <div className="row topnav-user">
            <NotificationBell enabled={streamEnabled} active={active === "notifications"} />
            <Link to="/candidate/profile" className="row"
              title={user?.fullName ? `${user.fullName} – Hồ sơ & mật khẩu` : "Hồ sơ & mật khẩu"}
              aria-current={active === "profile" ? "page" : undefined}
              style={{ gap: 10, color: "inherit", textDecoration: "none", flexWrap: "nowrap" }}>
              <span className="avatar" aria-hidden="true">{initials(user?.fullName)}</span>
              <span className="topnav-user-name">{user?.fullName}</span>
            </Link>
            <span className="topnav-sep" />
            <button type="button" className="btn btn-sm" onClick={onLogout}>Đăng xuất</button>
          </div>
        )}
      </div>
    </header>
  );
}
