import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { MAX_PAGE_SIZE, jobsApi, type JobDto } from "../api/client";
import { followCompany, getCompany, unfollowCompany, type CompanyDto } from "../api/mock/companyMock";
import { EmptyNote, JobCard, SiteHeader } from "../components/common";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { mapJob } from "../utils/mappers";

/** Màn P05 · Chi tiết công ty (design canvas CompanyDetail.dc.html). */
export function CompanyDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toast } = useToast();

  const [company, setCompany] = useState<CompanyDto | null>(null);
  const [companyError, setCompanyError] = useState<string | null>(null);
  const [remoteJobs, setRemoteJobs] = useState<JobDto[] | null>(null);
  const [levelFilter, setLevelFilter] = useState("all");
  const [activeTab, setActiveTab] = useState<"about" | "jobs">("about");
  const [following, setFollowing] = useState(false);

  useEffect(() => {
    const numericId = Number(id);
    if (!id || Number.isNaN(numericId)) {
      setCompanyError("Mã công ty không hợp lệ.");
      return;
    }
    setCompany(null);
    setCompanyError(null);
    setFollowing(false);

    getCompany(numericId)
      .then((c) => {
        setCompany(c);
        setFollowing(Boolean(c.following));
      })
      .catch((e: unknown) => {
        setCompanyError(e instanceof Error ? e.message : "Không tìm thấy thông tin công ty.");
      });
  }, [id]);

  useEffect(() => {
    jobsApi
      .list({ size: MAX_PAGE_SIZE })
      .then((page) => setRemoteJobs(page.content))
      .catch(() => {
        setRemoteJobs([]);
        toast("Không tải được danh sách việc làm của công ty.");
      });
  }, [toast]);

  const companyJobs = useMemo(() => {
    if (!company || !remoteJobs) return [];
    const targetName = company.name.trim().toLowerCase();
    return remoteJobs
      .filter((j) => (j.company ?? "").trim().toLowerCase() === targetName)
      .map(mapJob);
  }, [company, remoteJobs]);

  const jobLevels = useMemo(
    () => [...new Set(companyJobs.map((j) => j.level).filter(Boolean))],
    [companyJobs]
  );

  const visibleJobs = useMemo(
    () =>
      levelFilter === "all"
        ? companyJobs
        : companyJobs.filter((j) => j.level === levelFilter),
    [companyJobs, levelFilter]
  );

  async function toggleFollow() {
    if (!company) return;
    if (!user) {
      toast("Vui lòng đăng nhập để theo dõi công ty.");
      navigate("/login");
      return;
    }
    try {
      const res = following ? await unfollowCompany(company.id) : await followCompany(company.id);
      setFollowing(res.following);
      setCompany((prev) => (prev ? { ...prev, following: res.following, followersCount: res.followersCount } : prev));
      toast(
        res.following
          ? `Đã theo dõi ${company.name}`
          : `Đã bỏ theo dõi ${company.name}`
      );
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : "Không thể cập nhật theo dõi công ty.");
    }
  }

  function openJob(jobId: string, title: string) {
    if (user?.role === "CANDIDATE") {
      navigate(`/candidate/jobs/${jobId}`);
      return;
    }
    navigate(`/jobs?keyword=${encodeURIComponent(title)}`);
  }

  return (
    <>
      <SiteHeader mode={user?.role === "CANDIDATE" ? "candidate" : "public"} active="companies" />

      {companyError ? (
        <div className="wrap page-hl">
          <EmptyNote>
            {companyError}{" "}
            <Link to="/companies" className="btn btn-link small">
              Quay lại danh sách công ty
            </Link>
          </EmptyNote>
        </div>
      ) : company === null ? (
        <div className="wrap page-hl">
          <p className="muted">Đang tải thông tin công ty…</p>
        </div>
      ) : (
        <>
          <section
            style={{
              background: company.coverUrl
                ? `linear-gradient(rgba(0,0,0,.55), rgba(0,0,0,.55)), center / cover no-repeat url("${company.coverUrl}")`
                : "var(--ink)",
              color: "var(--bg)",
            }}
          >
            <div
              className="wrap"
              style={{
                paddingTop: 40,
                paddingBottom: 32,
                display: "flex",
                gap: 24,
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              {company.logoUrl ? (
                <img
                  className="logo logo-lg"
                  src={company.logoUrl}
                  alt={`Logo ${company.name}`}
                  style={{ background: "var(--paper)", width: 112, height: 112, objectFit: "contain" }}
                />
              ) : (
                <span
                  className="logo logo-lg"
                  style={{ background: "var(--paper)", width: 112, height: 112, fontSize: 32 }}
                >
                  {company.logo}
                </span>
              )}
              <div style={{ flex: "1 1 420px", display: "flex", flexDirection: "column", gap: 8 }}>
                <div className="row" style={{ gap: 8 }}>
                  {company.status === "ACTIVE" ? (
                    <span className="badge b-ok" style={{ background: "var(--ok)", color: "var(--ok-soft)" }}>
                      Đã xác minh
                    </span>
                  ) : (
                    <span className="badge b-warn">{company.status}</span>
                  )}
                </div>
                <h1 style={{ color: "var(--surface)", fontSize: 40 }}>{company.name}</h1>
                <p style={{ color: "var(--line)" }}>{company.tagline}</p>
                <div className="row small" style={{ gap: "6px 18px", color: "var(--line)" }}>
                  <span>{company.city}</span>
                  <span>{company.size}</span>
                  <span>{company.workMode}</span>
                  <span>{company.website}</span>
                </div>
              </div>
              <div className="row">
                <button
                  type="button"
                  className="btn"
                  aria-pressed={following}
                  style={{
                    background: following ? "var(--brand-soft)" : "var(--surface)",
                    color: following ? "var(--brand-deep)" : "var(--ink)",
                  }}
                  onClick={toggleFollow}
                >
                  {following ? "Đang theo dõi" : "Theo dõi công ty"}
                </button>
                <a
                  href="#jobs"
                  className="btn"
                  style={{ borderColor: "var(--muted)", color: "var(--surface)" }}
                  onClick={() => setActiveTab("jobs")}
                >
                  {companyJobs.length} việc đang tuyển
                </a>
              </div>
            </div>
            <div className="wrap">
              <div className="tabs" style={{ borderBottom: 0 }}>
                <a
                  href="#about"
                  className={activeTab === "about" ? "tab tab-on" : "tab"}
                  style={{
                    color: activeTab === "about" ? "var(--surface)" : "var(--line)",
                    borderBottomColor: activeTab === "about" ? "var(--brand-soft)" : "transparent",
                  }}
                  onClick={() => setActiveTab("about")}
                >
                  Giới thiệu
                </a>
                <a
                  href="#jobs"
                  className={activeTab === "jobs" ? "tab tab-on" : "tab"}
                  style={{
                    color: activeTab === "jobs" ? "var(--surface)" : "var(--line)",
                    borderBottomColor: activeTab === "jobs" ? "var(--brand-soft)" : "transparent",
                  }}
                  onClick={() => setActiveTab("jobs")}
                >
                  Việc làm
                  <span
                    className="count"
                    style={{ background: "var(--ink-soft)", color: "var(--surface)" }}
                  >
                    {companyJobs.length}
                  </span>
                </a>
              </div>
            </div>
          </section>

          <div
            className="wrap"
            style={{
              paddingTop: 28,
              paddingBottom: 64,
              display: "flex",
              flexDirection: "column",
              gap: 20,
            }}
          >
            <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "flex-start" }}>
              <main style={{ flex: "999 1 560px", minWidth: 0, display: "flex", flexDirection: "column", gap: 20 }}>
                <section id="about" className="card" style={{ padding: 28, display: "flex", flexDirection: "column", gap: 14 }}>
                  <h2 style={{ fontSize: 24 }}>Giới thiệu công ty</h2>
                  <p style={{ color: "var(--ink-soft)" }}>{company.about}</p>
                  <h3 style={{ fontSize: 18, marginTop: 8 }}>Chuyên môn của chúng tôi</h3>
                  <div className="row" style={{ gap: 6 }}>
                    {company.skills.map((skill) => (
                      <span key={skill} className="tag">{skill}</span>
                    ))}
                  </div>
                  <h3 style={{ fontSize: 18, marginTop: 8 }}>Vì sao bạn sẽ thích làm việc tại đây</h3>
                  <ul style={{ margin: 0, paddingLeft: 20, display: "grid", gap: 6, color: "var(--ink-soft)" }}>
                    {company.perks.map((perk) => (
                      <li key={perk}>{perk}</li>
                    ))}
                  </ul>
                </section>

                <section id="jobs" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div className="between">
                    <h2 style={{ fontSize: 24 }}>Việc làm đang tuyển</h2>
                    {jobLevels.length > 0 ? (
                      <label className="row small" style={{ gap: 8 }}>
                        <span className="muted">Lọc</span>
                        <select
                          className="input"
                          aria-label="Lọc cấp bậc việc làm"
                          style={{ height: 38, width: "auto" }}
                          value={levelFilter}
                          onChange={(e) => setLevelFilter(e.target.value)}
                        >
                          <option value="all">Tất cả cấp bậc</option>
                          {jobLevels.map((lv) => (
                            <option key={lv} value={lv}>{lv}</option>
                          ))}
                        </select>
                      </label>
                    ) : null}
                  </div>

                  {remoteJobs === null ? (
                    <p className="muted">Đang tải danh sách việc làm…</p>
                  ) : visibleJobs.length === 0 ? (
                    <EmptyNote>
                      Hiện chưa có tin tuyển dụng phù hợp cho {company.name}.{" "}
                      <Link to="/jobs" className="btn btn-link small">
                        Xem tất cả việc làm IT
                      </Link>
                    </EmptyNote>
                  ) : (
                    <>
                      {visibleJobs.map((job, idx) => (
                        <JobCard
                          key={job.id}
                          job={job}
                          delayMs={idx * 40}
                          onClick={() => openJob(job.id, job.title)}
                        />
                      ))}
                      <Link to="/jobs" className="btn btn-g" style={{ alignSelf: "center" }}>
                        Xem tất cả việc làm
                      </Link>
                    </>
                  )}
                </section>
              </main>

              <aside style={{ flex: "1 1 300px", minWidth: 0, maxWidth: 380, display: "flex", flexDirection: "column", gap: 20 }}>
                <section className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <h4>Thông tin chung</h4>
                  <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "120px 1fr", gap: 10, fontSize: 14 }}>
                    <dt className="muted">Ngành</dt>
                    <dd style={{ margin: 0 }}>{company.industry}</dd>
                    <dt className="muted">Quy mô</dt>
                    <dd style={{ margin: 0 }}>{company.size}</dd>
                    <dt className="muted">Thành lập</dt>
                    <dd style={{ margin: 0 }}>{company.founded}</dd>
                    <dt className="muted">Ngày làm việc</dt>
                    <dd style={{ margin: 0 }}>{company.workingDays}</dd>
                    <dt className="muted">Làm thêm giờ</dt>
                    <dd style={{ margin: 0 }}>{company.overtime}</dd>
                    <dt className="muted">Website</dt>
                    <dd style={{ margin: 0 }}>
                      <a
                        href={`https://${company.website}`}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: "var(--brand)" }}
                      >
                        {company.website}
                      </a>
                    </dd>
                  </dl>
                </section>

                <section className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <h4>Văn phòng</h4>
                  <p className="small">{company.address}</p>
                  <div
                    style={{
                      height: 160,
                      background: "var(--sky)",
                      border: "1px solid var(--line)",
                      display: "grid",
                      placeItems: "center",
                    }}
                    className="small muted"
                  >
                    [Bản đồ]
                  </div>
                </section>
              </aside>
            </div>
          </div>
        </>
      )}
    </>
  );
}
