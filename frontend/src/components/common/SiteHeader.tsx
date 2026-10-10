import { Link } from "react-router-dom";
import type { HeaderMode, NavKey } from "../../types";
import { Brand } from "./Brand";
import { Button } from "./Button";
import { classNames } from "../../utils/format";

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

function navForMode(mode: HeaderMode): {
  home: string;
  links: NavItem[];
} {
  if (mode === "public") {
    return {
      home: "/",
      links: [
        { to: "/", key: "jobs", label: "Việc làm" },
        { to: "/login", key: "login", label: "Công cụ AI" },
      ],
    };
  }
  if (mode === "recruiter") {
    return {
      home: "/recruiter",
      links: [
        { to: "/recruiter", key: "home", label: "Tổng quan" },
        { to: "/recruiter/jobs", key: "jobs", label: "Đăng tuyển" },
        { to: "/recruiter/candidates", key: "candidates", label: "Ứng viên" },
        { to: "/recruiter/matching", key: "matching", label: "Matching AI" },
        { to: "/recruiter/interviews", key: "interviews", label: "Phỏng vấn" },
      ],
    };
  }
  return {
    home: "/candidate",
    links: [
      { to: "/candidate", key: "jobs", label: "Việc làm" },
      { to: "/candidate/matching", key: "matching", label: "Phù hợp với tôi" },
      { to: "/candidate/cv", key: "cv", label: "Hồ sơ / CV" },
      { to: "/candidate/interview", key: "interview", label: "Phỏng vấn AI" },
    ],
  };
}

export function SiteHeader({
  active,
  mode,
  userLocation = "Quận 1, TP. Hồ Chí Minh",
}: SiteHeaderProps) {
  const { home, links } = navForMode(mode);

  return (
    <header className="site-header">
      <div className="site-header-inner">
        <Brand to={home} />
        <nav className="nav-links">
          {links.map((l) => (
            <Link
              key={l.key}
              to={l.to}
              className={classNames(active === l.key && "active")}
            >
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="header-actions">
          {mode === "public" ? (
            <>
              <span className="loc-pill">Gần: {userLocation}</span>
              <Button variant="ghost" size="sm" to="/login">
                Đăng nhập
              </Button>
              <Button variant="primary" size="sm" to="/login">
                Tạo tài khoản
              </Button>
            </>
          ) : null}
          {mode === "recruiter" ? (
            <>
              <Button variant="ghost" size="sm" to="/">
                Về trang việc làm
              </Button>
              <Button variant="primary" size="sm" to="/login">
                Đổi vai trò
              </Button>
            </>
          ) : null}
          {mode === "candidate" ? (
            <>
              <span className="loc-pill">Gần: {userLocation}</span>
              <Button variant="ghost" size="sm" to="/">
                Trang chủ
              </Button>
              <Button variant="primary" size="sm" to="/login">
                Đổi vai trò
              </Button>
            </>
          ) : null}
        </div>
      </div>
    </header>
  );
}
