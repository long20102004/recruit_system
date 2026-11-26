import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAdminDashboard, type AdminDashboardData } from "../../api/mock/adminMock";
import { listCompanies, type CompanyDto } from "../../api/mock/companyMock";
import { EmptyNote, RecruiterLayout } from "../../components/common";
import { useToast } from "../../context/ToastContext";
import { shortDate } from "../../utils/format";

/** Màn AD01 · Dashboard quản trị (design canvas AdminDashboard.dc.html). */
export function AdminDashboardPage() {
  const { toast } = useToast();
  const [dashboard, setDashboard] = useState<AdminDashboardData | null>(null);
  const [pendingCompanies, setPendingCompanies] = useState<CompanyDto[] | null>(null);
  const [activeCompaniesCount, setActiveCompaniesCount] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([
      getAdminDashboard(),
      listCompanies({ status: "PENDING" }),
      listCompanies({ status: "ACTIVE" }),
    ])
      .then(([dash, pending, active]) => {
        setDashboard(dash);
        setPendingCompanies(pending);
        setActiveCompaniesCount(active.length);
      })
      .catch((e: unknown) => {
        toast(e instanceof Error ? e.message : "Không tải được dữ liệu tổng quan.");
      });
  }, [toast]);

  const maxRoleCount = dashboard
    ? Math.max(1, ...dashboard.roles.map((r) => r.count))
    : 1;

  return (
    <RecruiterLayout active="adminHome">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <p className="kicker">Quản trị hệ thống</p>
          <h1 style={{ fontSize: 32, marginTop: 4 }}>Tổng quan</h1>
        </div>
        <div className="row" style={{ gap: 8 }}>
          <Link to="/admin/companies" className="btn btn-g btn-sm">Duyệt công ty</Link>
          <Link to="/admin/jobs" className="btn btn-g btn-sm">Quản lý tin</Link>
          <Link to="/admin/cv-templates" className="btn btn-g btn-sm">Mẫu CV</Link>
        </div>
      </div>

      {dashboard === null ? (
        <p className="muted">Đang tải số liệu…</p>
      ) : (
        <>
          <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 200px), 1fr))", gap: 20 }}>
            {dashboard.kpis.map((kpi) => {
              const displayValue =
                kpi.id === "companies" && activeCompaniesCount !== null
                  ? String(activeCompaniesCount)
                  : kpi.value;
              const displayNote =
                kpi.id === "companies" && pendingCompanies !== null
                  ? `${pendingCompanies.length} chờ duyệt`
                  : kpi.note;
              return (
                <div key={kpi.id} className="stat">
                  <p className="l">{kpi.label}</p>
                  <p className="v">{displayValue}</p>
                  {displayNote ? <p className="tiny muted">{displayNote}</p> : null}
                </div>
              );
            })}
          </section>

          <section style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>
            <div className="card" style={{ flex: "999 1 480px", display: "flex", flexDirection: "column", gap: 4 }}>
              <div className="between" style={{ marginBottom: 8 }}>
                <h3 style={{ fontSize: 18 }}>
                  Công ty chờ duyệt
                  <span className="count">{pendingCompanies?.length ?? 0}</span>
                </h3>
                <Link to="/admin/companies" className="small" style={{ color: "var(--brand)", fontWeight: 650 }}>
                  Mở hàng chờ
                </Link>
              </div>
              {pendingCompanies === null ? (
                <p className="muted small">Đang tải…</p>
              ) : pendingCompanies.length === 0 ? (
                <EmptyNote>Không có công ty nào đang chờ duyệt.</EmptyNote>
              ) : (
                pendingCompanies.slice(0, 5).map((p) => (
                  <div
                    key={p.id}
                    className="between"
                    style={{ padding: "12px 0", borderTop: "1px solid var(--line)" }}
                  >
                    <div className="row" style={{ gap: 12, flexWrap: "nowrap" }}>
                      <span className="logo logo-sm">{p.logo}</span>
                      <div>
                        <p style={{ fontWeight: 650, fontSize: 14 }}>{p.name}</p>
                        <p className="tiny muted">{p.industry} · gửi {shortDate(p.submittedAt)}</p>
                      </div>
                    </div>
                    <Link to={`/admin/companies?id=${p.id}`} className="btn btn-g btn-sm">
                      Xem xét
                    </Link>
                  </div>
                ))
              )}
            </div>

            <div className="card" style={{ flex: "1 1 320px", display: "flex", flexDirection: "column", gap: 10 }}>
              <h3 style={{ fontSize: 18 }}>Người dùng theo vai trò</h3>
              {dashboard.roles.map((r) => {
                const widthPct = Math.max(1, Math.round((r.count / maxRoleCount) * 100));
                return (
                  <div
                    key={r.role}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "110px 1fr 56px",
                      gap: 12,
                      alignItems: "center",
                      fontSize: 14,
                    }}
                  >
                    <span>{r.label}</span>
                    <div style={{ height: 18, background: "var(--sky)" }}>
                      <div style={{ height: "100%", background: "var(--brand)", width: `${widthPct}%` }} />
                    </div>
                    <strong style={{ textAlign: "right" }}>{r.count.toLocaleString("vi-VN")}</strong>
                  </div>
                );
              })}
              <p className="help" style={{ marginTop: 6 }}>
                {dashboard.lockedUsersCount} tài khoản đang bị khoá.{" "}
                <Link to="/admin/users" style={{ color: "var(--brand)", fontWeight: 600 }}>
                  Quản lý người dùng
                </Link>
              </p>
            </div>
          </section>

          <section className="stack" style={{ gap: 12 }}>
            <h2 style={{ fontSize: 22 }}>Hoạt động gần đây</h2>
            <div className="tbl-box">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Thời gian</th>
                    <th>Sự kiện</th>
                    <th>Đối tượng</th>
                    <th>Thực hiện</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.activityLog.map((entry) => (
                    <tr key={entry.id}>
                      <td className="small muted">{entry.time}</td>
                      <td>
                        <span className={entry.badgeClass}>{entry.event}</span>
                      </td>
                      <td style={{ fontWeight: 600 }}>{entry.target}</td>
                      <td className="small">{entry.actor}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </RecruiterLayout>
  );
}
