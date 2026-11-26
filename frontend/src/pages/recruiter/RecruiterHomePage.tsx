import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button, EmptyNote, RecruiterLayout, Can } from "../../components/common";
import {
  MAX_PAGE_SIZE,
  applicationsApi,
  dashboardApi,
  jobsApi,
  type ApplicationDto,
  type JobDto,
  type RecruiterStatsDto,
} from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { applicationBadge, initials, jobBadge, shortDate } from "../../utils/format";

export function RecruiterHomePage() {
  const { toast } = useToast();
  const { can } = useAuth();
  const canReadJobs = can("job:read-own");
  const canReadApps = can("application:read-received");
  const [stats, setStats] = useState<RecruiterStatsDto | null>(null);
  const [jobs, setJobs] = useState<JobDto[]>([]);
  const [apps, setApps] = useState<ApplicationDto[]>([]);
  const [days, setDays] = useState(30);
  const [now] = useState(() => Date.now());

  useEffect(() => {
    Promise.all([
      dashboardApi.recruiter(),
      canReadJobs ? jobsApi.mine({ size: MAX_PAGE_SIZE }).then((p) => p.content) : Promise.resolve([]),
      canReadApps ? applicationsApi.recruiter({ size: MAX_PAGE_SIZE }).then((p) => p.content) : Promise.resolve([]),
    ])
      .then(([s, j, a]) => {
        setStats(s);
        setJobs(j);
        setApps(a);
      })
      .catch((e) => toast(e.message));
  }, [toast, canReadJobs, canReadApps]);


  // Đơn trong khoảng thời gian đang chọn (theo ngày nộp) cho chỉ số "Đơn mới" và phễu.
  const inRange = apps.filter((a) => a.appliedAt && now - Date.parse(a.appliedAt) <= days * 86_400_000);
  const count = (st: string) => inRange.filter((a) => a.status === st).length;
  const drafts = jobs.filter((j) => j.status === "DRAFT").length;
  const company = jobs[0]?.company;
  const funnel: [string, number][] = [
    ["Đã nộp", inRange.length],
    ["Đang xem xét", count("REVIEWING")],
    ["Phỏng vấn", count("INTERVIEW")],
    ["Trúng tuyển", count("HIRED")],
    ["Từ chối", count("REJECTED")],
  ];
  const max = Math.max(1, inRange.length);
  const perJob = (jobId: number) => apps.filter((a) => a.jobId === jobId).length;
  const recent = [...apps].sort((x, y) => (y.appliedAt ?? "").localeCompare(x.appliedAt ?? "")).slice(0, 8);

  return (
    <RecruiterLayout active="home">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <p className="kicker">{company ?? "Nhà tuyển dụng"}</p>
          <h1 style={{ fontSize: 32, marginTop: 4 }}>Tổng quan tuyển dụng</h1>
        </div>
        <div className="row">
          <select className="input" aria-label="Khoảng thời gian" style={{ width: "auto" }} value={days}
            onChange={(e) => setDays(Number(e.target.value))}>
            <option value={30}>30 ngày qua</option>
            <option value={7}>7 ngày qua</option>
          </select>
          <Can perm="job:create">
            <Button variant="primary" to="/recruiter/jobs/new">+ Đăng tin mới</Button>
          </Can>
        </div>
      </div>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 200px), 1fr))", gap: 20 }}>
        <div className="stat"><p className="l">Tin đang mở</p>
          <p className="v">{stats?.openJobsCount ?? jobs.filter((j) => j.status === "PUBLISHED").length}</p>
          <p className="tiny muted">{drafts ? `${drafts} tin nháp` : "Hiển thị trên trang tìm việc"}</p></div>
        <div className="stat"><p className="l">Đơn mới ({days} ngày)</p>
          <p className="v">{inRange.length}</p>
          <p className="tiny muted">Tổng {stats?.applicationsCount ?? apps.length} đơn</p></div>
        <div className="stat"><p className="l">Chờ xử lý</p>
          <p className="v">{count("SUBMITTED")}</p>
          <p className="tiny muted">Đơn ở trạng thái Đã nộp</p></div>
        <div className="stat"><p className="l">Câu hỏi phỏng vấn</p>
          <p className="v">{stats?.questionsCount ?? 0}</p>
          <p className="tiny muted">Ngân hàng câu hỏi</p></div>
      </section>

      <section style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>
        <div className="card" style={{ flex: "1 1 360px", display: "flex", flexDirection: "column", gap: 12 }}>
          <h3 style={{ fontSize: 18 }}>Phễu ứng viên</h3>
          {funnel.map(([n, v]) => (
            <div key={n} style={{ display: "grid", gridTemplateColumns: "120px 1fr 40px", gap: 12, alignItems: "center", fontSize: 14 }}>
              <span>{n}</span>
              <div style={{ height: 22, background: "var(--sky)" }}>
                <div style={{ height: "100%", width: `${(v / max) * 100}%`, background: n === "Từ chối" ? "#cfc6ba" : "var(--brand)" }} />
              </div>
              <strong style={{ textAlign: "right" }}>{v}</strong>
            </div>
          ))}
        </div>
        <div className="card" style={{ flex: "1 1 360px", display: "flex", flexDirection: "column", gap: 4 }}>
          <div className="between" style={{ marginBottom: 8 }}>
            <h3 style={{ fontSize: 18 }}>Tin của bạn</h3>
            <Can perm="job:read-own">
              <Link to="/recruiter/jobs" className="small" style={{ color: "var(--brand)", fontWeight: 650 }}>Tất cả tin</Link>
            </Can>
          </div>
          {jobs.length === 0 ? <p className="small muted">Chưa có tin. Hãy đăng vị trí mới.</p> : jobs.slice(0, 5).map((j) => {
            const b = jobBadge(j.status);
            return (
              <div key={j.id} className="between" style={{ padding: "10px 0", borderTop: "1px solid var(--line)" }}>
                <div>
                  <p style={{ fontWeight: 650, fontSize: 14 }}>{j.title}</p>
                  <p className="tiny muted">{perJob(j.id)} ứng viên</p>
                </div>
                <span className={b.cls}>{b.label}</span>
              </div>
            );
          })}
        </div>
      </section>

      <section className="stack" style={{ gap: 12 }}>
        <div className="between">
          <h2 style={{ fontSize: 22 }}>Đơn ứng tuyển mới</h2>
          <Link to="/recruiter/candidates" className="btn btn-link">Quản lý đơn →</Link>
        </div>
        {recent.length === 0 ? (
          <EmptyNote>Chưa có đơn ứng tuyển.</EmptyNote>
        ) : (
          <div className="tbl-box">
            <table className="tbl">
              <thead><tr><th>Ứng viên</th><th>Vị trí</th><th>Nộp</th><th>Trạng thái</th></tr></thead>
              <tbody>
                {recent.map((a) => {
                  const b = applicationBadge(a.status);
                  return (
                    <tr key={a.id}>
                      <td>
                        <div className="row" style={{ gap: 10, flexWrap: "nowrap" }}>
                          <span className="avatar">{initials(a.candidateName)}</span>
                          <span style={{ fontWeight: 650 }}>{a.candidateName}</span>
                        </div>
                      </td>
                      <td className="small">{a.jobTitle}</td>
                      <td className="small muted">{shortDate(a.appliedAt)}</td>
                      <td><span className={b.cls}>{b.label}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </RecruiterLayout>
  );
}
