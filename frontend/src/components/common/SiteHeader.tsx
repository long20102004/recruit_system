import { Link, useNavigate } from "react-router-dom";
import type { HeaderMode, NavKey } from "../../types";
import { Brand } from "./Brand";
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

const PUBLIC_LINKS: NavItem[] = [{ to: "/jobs", key: "jobs", label: "Việc làm IT" }];

const CANDIDATE_LINKS: NavItem[] = [
  { to: "/candidate", key: "home", label: "Tổng quan" },
  { to: "/jobs", key: "jobs", label: "Việc làm IT" },
  { to: "/candidate/matching", key: "matching", label: "Việc phù hợp" },
  { to: "/candidate/cv", key: "cv", label: "CV của tôi" },
  { to: "/candidate/interview", key: "interview", label: "Phỏng vấn" },
];

export function SiteHeader({ active, mode, userLocation }: SiteHeaderProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const candidate = mode !== "public";
  const links = candidate ? CANDIDATE_LINKS : PUBLIC_LINKS;

  function onLogout() {
    logout();
    navigate("/login");
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
            </div>
          )
        ) : (
          <div className="row" style={{ gap: 10 }}>
            <Link to="/candidate/profile" className="row" title="Hồ sơ & mật khẩu"
              aria-current={active === "profile" ? "page" : undefined}
              style={{ gap: 10, color: "inherit", textDecoration: "none" }}>
              <span className="avatar" aria-hidden="true">{initials(user?.fullName)}</span>
              <span style={{ fontSize: 14, fontWeight: 600 }}>{user?.fullName}</span>
            </Link>
            <span className="topnav-sep" />
            <button type="button" className="btn btn-sm" onClick={onLogout}>Đăng xuất</button>
          </div>
        )}
      </div>
    </header>
  );
}
