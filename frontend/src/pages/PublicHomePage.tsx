import { useEffect, useMemo, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Button, EmptyNote, JobCard, JobLogo, SiteHeader } from "../components/common";
import { jobsApi, matchingApi, type JobDto, type MatchDto } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { mapJob, mapMatch } from "../utils/mappers";
import { filterJobs, jobById, matchForJob } from "../utils/jobs";
import { pct } from "../utils/format";
import { accountPath } from "../utils/account";

export function PublicHomePage() {
  const { toast } = useToast();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [keyword, setKeyword] = useState("");
  const [city, setCity] = useState("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [remoteJobs, setRemoteJobs] = useState<JobDto[]>([]);
  const [matches, setMatches] = useState<ReturnType<typeof mapMatch>[]>([]);

  useEffect(() => {
    jobsApi
      .list()
      .then((list) => {
        setRemoteJobs(list);
      })
      .catch(() => {
        toast("Không tải được danh sách việc làm. Thử lại sau.");
      });
  }, [toast]);

  useEffect(() => {
    if (!user || user.role !== "CANDIDATE") return;
    matchingApi
      .mine()
      .then((list: MatchDto[]) => setMatches(list.map(mapMatch)))
      .catch(() => undefined);
  }, [user]);

  const allJobs = useMemo(
    () => (remoteJobs.length ? remoteJobs.map(mapJob) : []),
    [remoteJobs]
  );

  const jobs = useMemo(
    () => filterJobs(allJobs, { keyword, city }),
    [allJobs, keyword, city]
  );

  const activeId =
    selectedId && jobs.some((j) => j.id === selectedId)
      ? selectedId
      : jobs[0]?.id ?? null;
  const selected = activeId ? jobById(allJobs, activeId) : undefined;
  const match = activeId ? matchForJob(matches, activeId) : undefined;

  /** Kỹ năng xuất hiện nhiều nhất trong các tin đang mở: dùng làm "Từ khóa phổ biến". */
  const popular = useMemo(() => {
    const count = new Map<string, number>();
    for (const j of allJobs) for (const k of j.requiredSkills) count.set(k, (count.get(k) ?? 0) + 1);
    return [...count.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8).map(([k]) => k);
  }, [allJobs]);
  const cities = useMemo(
    () => [...new Set(allJobs.map((j) => j.city).filter(Boolean))].sort(),
    [allJobs]
  );
  const isCandidate = user?.role === "CANDIDATE";
  const isRecruiter = user?.role === "RECRUITER" || user?.role === "ADMIN";

  function goApply() {
    if (!user) {
      navigate("/register");
      return;
    }
    navigate(accountPath(user));
  }

  return (
    <>
      <SiteHeader active="jobs" mode="public" />

      <section style={{ padding: "56px 0 32px", borderBottom: "1px solid var(--line)" }}>
        <div className="wrap" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <p className="kicker">{allJobs.length} việc làm IT đang tuyển</p>
          <h1 style={{ maxWidth: 820, fontSize: 52 }}>Việc làm IT hợp với bạn, xếp theo kỹ năng và CV.</h1>
          <p className="muted" style={{ maxWidth: 640, fontSize: 17 }}>
            Tìm theo vị trí, kỹ năng hoặc công ty. Tải CV lên để xem mức phù hợp và luyện phỏng vấn cho đúng tin bạn
            ứng tuyển.
          </p>
          <form className="search" role="search" style={{ marginTop: 8 }} onSubmit={(e) => e.preventDefault()}>
            <label className="seg" style={{ flex: "3 1 320px" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" strokeWidth="2" aria-hidden="true">
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-3.5-3.5" />
              </svg>
              <input type="search" placeholder="Vị trí, kỹ năng, công ty…" aria-label="Từ khóa"
                value={keyword} onChange={(e) => setKeyword(e.target.value)} />
            </label>
            <label className="seg" style={{ flex: "1 1 200px" }}>
              <select aria-label="Thành phố" value={city} onChange={(e) => setCity(e.target.value)}>
                <option value="all">Tất cả thành phố</option>
                {cities.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
            <button type="submit" className="btn btn-p">Tìm việc</button>
          </form>
          {popular.length ? (
            <div className="row" style={{ gap: 8 }}>
              <span className="small muted" style={{ marginRight: 4 }}>Từ khóa phổ biến:</span>
              {popular.map((k) => (
                <button key={k} type="button" className={keyword === k ? "tag tag-on" : "tag"}
                  onClick={() => setKeyword(keyword === k ? "" : k)}>
                  {k}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </section>

      <section style={{ padding: "24px 0 56px" }}>
        <div className="wrap" style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "flex-start" }}>
          <div style={{ flex: "999 1 520px", minWidth: 0, display: "flex", flexDirection: "column", gap: 12 }}>
            <div className="between">
              <p>
                <strong className="disp" style={{ fontSize: 22 }}>{jobs.length}</strong>{" "}
                <span className="muted">
                  việc làm{keyword ? ` "${keyword}"` : ""}{city !== "all" ? ` tại ${city}` : ""}
                </span>
              </p>
              {keyword || city !== "all" ? (
                <button type="button" className="btn btn-link small"
                  onClick={() => { setKeyword(""); setCity("all"); }}>
                  Xóa lọc
                </button>
              ) : null}
            </div>
            {!user ? (
              <div className="note small">
                Đăng nhập và tải CV để xem % phù hợp trên từng tin.{" "}
                <Link to="/login" style={{ fontWeight: 700, textDecoration: "underline" }}>Đăng nhập</Link>
              </div>
            ) : null}
            {jobs.length === 0 ? (
              <EmptyNote>Chưa có tin phù hợp với bộ lọc hiện tại. Thử đổi thành phố hoặc từ khóa.</EmptyNote>
            ) : (
              jobs.map((job, i) => (
                <JobCard
                  key={job.id}
                  job={job}
                  match={matchForJob(matches, job.id)}
                  showMatch={isCandidate}
                  active={job.id === activeId}
                  delayMs={i * 40}
                  onClick={() => setSelectedId(job.id)}
                />
              ))
            )}
          </div>

          <aside className="card" style={{ flex: "1 1 380px", minWidth: 0, maxWidth: 460, position: "sticky", top: 16 }}>
            {selected ? (
              <>
                <div className="row" style={{ gap: 14, flexWrap: "nowrap", alignItems: "flex-start" }}>
                  <JobLogo initials={selected.logo} />
                  <div style={{ minWidth: 0 }}>
                    <h3>{selected.title}</h3>
                    <p className="small" style={{ color: "var(--brand)", fontWeight: 600 }}>{selected.company}</p>
                  </div>
                </div>
                <p className="salary-hl" style={{ marginTop: 14, fontSize: 17 }}>{selected.salary}</p>
                {isCandidate && match ? (
                  <p className="match" style={{ marginTop: 6 }}>{pct(match.score)}% phù hợp với CV của bạn</p>
                ) : null}
                <div className="row" style={{ marginTop: 14, gap: 8, flexWrap: "nowrap" }}>
                  <Button variant="primary" onClick={goApply} style={{ flex: 1 }}>
                    {isRecruiter ? "Trang tuyển dụng" : "Ứng tuyển"}
                  </Button>
                  {!isRecruiter ? (
                    <Button variant="ghost" to={user ? "/candidate/interview" : "/register"}>Luyện phỏng vấn</Button>
                  ) : null}
                </div>
                <dl style={{ margin: "18px 0 0", display: "grid", gridTemplateColumns: "120px 1fr", gap: "8px 12px", fontSize: 14 }}>
                  <dt className="muted">Địa điểm</dt><dd style={{ margin: 0 }}>{selected.location}</dd>
                  <dt className="muted">Hình thức</dt><dd style={{ margin: 0 }}>{selected.workType}</dd>
                  <dt className="muted">Cấp bậc</dt>
                  <dd style={{ margin: 0 }}>{selected.level}{selected.minYears ? ` · ${selected.minYears}+ năm` : ""}</dd>
                  <dt className="muted">Đăng</dt><dd style={{ margin: 0 }}>{selected.postedAgo}</dd>
                </dl>
                <div className="row" style={{ gap: 6, marginTop: 14 }}>
                  {selected.requiredSkills.map((s) => <span key={s} className="tag tag-on">{s}</span>)}
                  {selected.preferredSkills.map((s) => <span key={s} className="tag">{s}</span>)}
                </div>
                <hr className="hr" style={{ margin: "18px 0" }} />
                <h4>Mô tả công việc</h4>
                <p className="small" style={{ marginTop: 8, color: "var(--ink-soft)", whiteSpace: "pre-line" }}>
                  {selected.description || "Nhà tuyển dụng chưa thêm mô tả."}
                </p>
                {isCandidate && match?.reasons[0] ? (
                  <div className="note small" style={{ marginTop: 14 }}>{match.reasons[0]}</div>
                ) : !user ? (
                  <div className="note small" style={{ marginTop: 14 }}>
                    Tạo tài khoản ứng viên và tải CV để xem mức phù hợp theo hồ sơ của bạn.
                  </div>
                ) : null}
              </>
            ) : (
              <>
                <h3>Chi tiết việc làm</h3>
                <p className="muted small" style={{ marginTop: 6 }}>Chọn một tin bên trái để xem mô tả, kỹ năng và mức lương.</p>
              </>
            )}
          </aside>
        </div>
      </section>
    </>
  );
}
