import { useEffect, useMemo, useState } from "react";
import { ApplyModal, Button, EmptyNote, JobCard, JobLogo, SiteHeader, type ApplyTarget } from "../../components/common";
import {
  MAX_PAGE_SIZE,
  applicationsApi,
  cvsApi,
  jobsApi,
  matchingApi,
  type ApplicationDto,
  type JobDto,
  type MatchDto,
} from "../../api/client";
import { savedJobsMock } from "../../api/mock/candidateMock";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { mapJob, mapMatch } from "../../utils/mappers";
import { filterJobs, jobById, matchForJob } from "../../utils/jobs";
import { applicationBadge, pct, shortDate } from "../../utils/format";
import { Link, useSearchParams } from "react-router-dom";

export function CandidateHomePage() {
  const { user, can } = useAuth();
  const { toast } = useToast();
  const [searchParams] = useSearchParams();
  // Trang này gộp "Tổng quan" và "Việc làm IT" (specs: bỏ trang /jobs riêng cho ứng viên).
  const [keyword, setKeyword] = useState(() => searchParams.get("keyword") ?? "");
  const [city, setCity] = useState(() => searchParams.get("city") || "all");
  const [level, setLevel] = useState("all");
  const [workType, setWorkType] = useState("all");
  const [mode, setMode] = useState<"near" | "match">("near");
  const [jobs, setJobs] = useState<JobDto[]>([]);
  const [matches, setMatches] = useState<MatchDto[]>([]);
  const [cvReady, setCvReady] = useState(false);
  const [apps, setApps] = useState<ApplicationDto[]>([]);
  const [applying, setApplying] = useState<ApplyTarget | null>(null);
  const [savedCount, setSavedCount] = useState(0);

  useEffect(() => {
    // Dữ liệu mẫu (C07) cho tới khi có API việc đã lưu.
    savedJobsMock.list().then((xs) => setSavedCount(xs.length)).catch(() => setSavedCount(0));
  }, []);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [today] = useState(() =>
    new Date().toLocaleDateString("vi-VN", { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" })
  );

  useEffect(() => {
    jobsApi.list({ size: MAX_PAGE_SIZE }).then((p) => setJobs(p.content)).catch((e) => toast(e.message));
    applicationsApi.mine({ size: MAX_PAGE_SIZE }).then((p) => setApps(p.content)).catch(() => setApps([]));
    cvsApi
      .mine()
      .then(async (form) => {
        const ready = form.analyzed;
        setCvReady(ready);
        if (!ready) {
          setMatches([]);
          return;
        }
        setMatches((await matchingApi.mine({ size: MAX_PAGE_SIZE })).content);
      })
      .catch(() => {
        setCvReady(false);
        setMatches([]);
      });
  }, [toast]);

  const mapped = useMemo(() => jobs.map(mapJob), [jobs]);
  const matchResults = useMemo(() => matches.map(mapMatch), [matches]);

  const list = useMemo(() => {
    if (mode === "match") {
      const byScore = [...matchResults].sort((a, b) => b.score - a.score);
      const ranked = byScore
        .map((m) => mapped.find((j) => j.id === m.jobId))
        .filter(Boolean) as ReturnType<typeof mapJob>[];
      if (ranked.length > 0 || !cvReady) return ranked;
      return mapped;
    }
    return filterJobs(mapped, { keyword, city })
      .filter((j) => (level === "all" || j.level === level) && (workType === "all" || j.workType === workType));
  }, [mode, mapped, matchResults, keyword, city, level, workType, cvReady]);

  const options = (pick: (j: ReturnType<typeof mapJob>) => string) =>
    [...new Set(mapped.map(pick).filter(Boolean))].sort();

  const top = matchResults[0];
  const topJob = top ? mapped.find((j) => j.id === top.jobId) : undefined;
  const firstName = user?.fullName?.split(" ").slice(-1)[0] ?? "bạn";
  // Bấm thẻ việc chỉ đổi khung tóm tắt bên phải; nút "Chi tiết" mới mở trang chi tiết.
  const activeId =
    selectedId && list.some((job) => job.id === selectedId)
      ? selectedId
      : list[0]?.id ?? null;
  const selected = activeId ? jobById(mapped, activeId) : undefined;
  const selectedMatch = activeId ? matchForJob(matchResults, activeId) : undefined;

  function apply(jobId: string) {
    const job = jobById(mapped, jobId);
    if (!job) return;
    const m = cvReady ? matchForJob(matchResults, jobId) : undefined;
    setApplying({ id: job.id, title: job.title, company: job.company, location: job.location,
      matchPct: m ? pct(m.score) : null });
  }

  function onApplied() {
    setApplying(null);
    toast("Đã gửi đơn. Nhà tuyển dụng sẽ nhận được thông báo.");
    applicationsApi.mine({ size: MAX_PAGE_SIZE }).then((p) => setApps(p.content)).catch(() => undefined);
  }

  const countBy = (st: string) => apps.filter((a) => a.status === st).length;
  const recentApps = [...apps].sort((a, b) => (b.appliedAt ?? "").localeCompare(a.appliedAt ?? "")).slice(0, 4);

  return (
    <>
      <SiteHeader active="home" mode="candidate" />
      <div className="wrap" style={{ paddingTop: 32, paddingBottom: 64, display: "flex", flexDirection: "column", gap: 28 }}>
        <section className="between" style={{ alignItems: "flex-end" }}>
          <div>
            <p className="kicker">{today}</p>
            <h1 style={{ fontSize: 36, marginTop: 6 }}>
              Chào {firstName}
              {cvReady && matchResults.length > 0
                ? `, có ${matchResults.length} việc hợp với CV của bạn.`
                : ", tải CV để xem việc hợp với bạn."}
            </h1>
          </div>
        </section>

        <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 260px), 1fr))", gap: 16 }}>
          {top && topJob ? (
            <Link to={`/candidate/jobs/${topJob.id}`} className="card"
              style={{ background: "var(--ink)", borderColor: "var(--ink)", color: "#e9e2d7", display: "flex", flexDirection: "column", gap: 10 }}>
              <span className="badge b-gold" style={{ alignSelf: "flex-start" }}>Phù hợp nhất · {pct(top.score)}%</span>
              <p className="disp" style={{ fontSize: 19, color: "#fbf8f3" }}>{topJob.title}</p>
              <p className="small">{topJob.company} · {topJob.location}</p>
              <span className="small" style={{ color: "#b8c5f0", fontWeight: 650 }}>Xem chi tiết →</span>
            </Link>
          ) : (
            <Link to="/candidate/interview" className="card"
              style={{ background: "var(--ink)", borderColor: "var(--ink)", color: "#e9e2d7", display: "flex", flexDirection: "column", gap: 10 }}>
              <span className="badge b-gold" style={{ alignSelf: "flex-start" }}>Luyện phỏng vấn</span>
              <p className="disp" style={{ fontSize: 19, color: "#fbf8f3" }}>Ôn tập theo kỹ năng của bạn</p>
              <p className="small">Trả lời câu hỏi, AI chấm điểm và chỉ ra ý còn thiếu.</p>
              <span className="small" style={{ color: "#b8c5f0", fontWeight: 650 }}>Bắt đầu phiên →</span>
            </Link>
          )}
          <div className="card stack" style={{ gap: 10 }}>
            <div className="between">
              <h4>Hồ sơ của bạn</h4>
              <span className={cvReady ? "badge b-ok" : "badge b-warn"}>{cvReady ? "Đã phân tích" : "Chưa có CV"}</span>
            </div>
            <div className="meter"><span style={{ width: cvReady ? "100%" : "15%" }} /></div>
            <p className="small">
              {cvReady
                ? "CV đang được dùng để xếp hạng việc làm. Cập nhật CV khi có kinh nghiệm hoặc dự án mới."
                : "Tải CV PDF, AI sẽ điền sẵn kỹ năng, kinh nghiệm, học vấn."}
            </p>
            <Button variant="ghost" size="sm" to="/candidate/cv" style={{ alignSelf: "flex-start" }}>
              {cvReady ? "Cập nhật CV" : "Tải CV"}
            </Button>
          </div>
          <Link to="/candidate/applications" className="card" style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 14, color: "inherit" }}>
            <h4 style={{ gridColumn: "1 / -1" }}>Đơn ứng tuyển</h4>
            <div className="stat"><p className="l">Đã nộp</p><p className="v">{apps.length}</p></div>
            <div className="stat"><p className="l">Đang xem xét</p><p className="v">{countBy("REVIEWING")}</p></div>
            <div className="stat"><p className="l">Phỏng vấn</p><p className="v">{countBy("INTERVIEW")}</p></div>
            <div className="stat"><p className="l">Việc đã lưu</p><p className="v">{savedCount}</p></div>
          </Link>
        </section>

        <section style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "flex-start" }}>
          <div style={{ flex: "999 1 560px", minWidth: 0, display: "flex", flexDirection: "column", gap: 12 }}>
            <div className="between">
              <div>
                <p className="kicker">{mode === "match" ? "Gợi ý theo CV" : city === "all" ? "Tất cả khu vực" : city}</p>
                <h2>{mode === "match" ? "Việc làm dành cho bạn" : "Việc làm IT đang tuyển"}</h2>
              </div>
              <div className="tabs" role="tablist" style={{ borderBottom: 0, overflow: "visible", flexShrink: 0 }}>
                <button type="button" role="tab" aria-selected={mode === "near"}
                  className={mode === "near" ? "tab tab-on" : "tab"} onClick={() => setMode("near")}>
                  Theo khu vực
                </button>
                <button type="button" role="tab" aria-selected={mode === "match"}
                  className={mode === "match" ? "tab tab-on" : "tab"} onClick={() => setMode("match")}>
                  Phù hợp CV
                </button>
              </div>
            </div>
            {mode === "near" ? (
              <>
                <form className="search" role="search" onSubmit={(e) => e.preventDefault()}>
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
                      {options((j) => j.city).map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </label>
                  <button type="submit" className="btn btn-p">Tìm việc</button>
                </form>
                <div className="row small" style={{ gap: 8 }}>
                  <select className="input" aria-label="Cấp bậc" style={{ height: 38, width: "auto", paddingRight: 28, fontSize: 13.5, fontWeight: 600, borderRadius: 19 }} value={level} onChange={(e) => setLevel(e.target.value)}>
                    <option value="all">Cấp bậc: Tất cả</option>
                    {options((j) => j.level).map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                  <select className="input" aria-label="Hình thức" style={{ height: 38, width: "auto", paddingRight: 28, fontSize: 13.5, fontWeight: 600, borderRadius: 19 }} value={workType} onChange={(e) => setWorkType(e.target.value)}>
                    <option value="all">Hình thức: Tất cả</option>
                    {options((j) => j.workType).map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                  {keyword || city !== "all" || level !== "all" || workType !== "all" ? (
                    <button type="button" className="btn btn-link small"
                      onClick={() => { setKeyword(""); setCity("all"); setLevel("all"); setWorkType("all"); }}>
                      Xoá bộ lọc
                    </button>
                  ) : null}
                  <span className="muted" style={{ marginLeft: "auto" }}>{list.length} việc</span>
                </div>
              </>
            ) : (
              <p className="help">Xếp theo mức phù hợp với CV hiện tại. <Link to="/candidate/matching" style={{ color: "var(--brand)", fontWeight: 600 }}>Xem giải thích điểm →</Link></p>
            )}
            {mode === "match" && !cvReady ? (
              <EmptyNote>
                Tải CV để hệ thống phân tích hồ sơ. Việc phù hợp chỉ hiện sau khi CV đã được đọc.
                <div style={{ marginTop: 14 }}>
                  <Button variant="primary" size="sm" to="/candidate/cv">Tải CV</Button>
                </div>
              </EmptyNote>
            ) : list.length === 0 ? (
              <EmptyNote>Chưa có tin phù hợp.</EmptyNote>
            ) : (
              list.map((job, i) => (
                <JobCard
                  key={job.id}
                  job={job}
                  match={cvReady ? matchForJob(matchResults, job.id) : undefined}
                  showMatch={cvReady && matchResults.length > 0}
                  active={job.id === activeId}
                  delayMs={i * 40}
                  onClick={() => setSelectedId(job.id)}
                  onApply={can("application:apply") ? apply : undefined}
                />
              ))
            )}
          </div>

          <aside style={{ flex: "1 1 300px", minWidth: 0, maxWidth: 400, display: "flex", flexDirection: "column", gap: 20,
            position: "sticky", top: 16, maxHeight: "calc(100vh - 32px)", overflowY: "auto" }}>
            {selected ? (
              <section className="card stack" style={{ gap: 12 }}>
                <div className="row" style={{ gap: 12, flexWrap: "nowrap", alignItems: "flex-start" }}>
                  <JobLogo initials={selected.logo} />
                  <div style={{ minWidth: 0 }}>
                    <h4>{selected.title}</h4>
                    <p className="small muted">{selected.company} · {selected.location}</p>
                  </div>
                </div>
                <p className="salary-hl">{selected.salary}</p>
                {cvReady && selectedMatch ? <p className="match">{pct(selectedMatch.score)}% phù hợp</p> : null}
                <p className="small" style={{ color: "var(--ink-soft)" }}>{selected.description}</p>
                <div className="row" style={{ gap: 6 }}>
                  {selected.requiredSkills.map((s) => <span key={s} className="tag tag-on">{s}</span>)}
                  {selected.preferredSkills.map((s) => <span key={s} className="tag">{s}</span>)}
                </div>
                <div className="row" style={{ gap: 8 }}>
                  <Button variant="primary" size="sm" onClick={() => apply(selected.id)}>Ứng tuyển</Button>
                  <Button variant="ghost" size="sm" to={`/candidate/jobs/${selected.id}`}>Chi tiết</Button>
                </div>
              </section>
            ) : null}
            <section className="card stack" style={{ gap: 4 }}>
              <div className="between" style={{ marginBottom: 6 }}>
                <h4>Đơn gần đây</h4>
                <Link to="/candidate/applications" className="small" style={{ color: "var(--brand)", fontWeight: 650 }}>Tất cả</Link>
              </div>
              {recentApps.length === 0 ? (
                <p className="small muted">Bạn chưa nộp đơn nào.</p>
              ) : (
                recentApps.map((a) => {
                  const b = applicationBadge(a.status);
                  return (
                    <div key={a.id} style={{ padding: "10px 0", borderTop: "1px solid var(--line)", display: "flex", flexDirection: "column", gap: 4 }}>
                      <p style={{ fontWeight: 650, fontSize: 14 }}>{a.jobTitle}</p>
                      <div className="between">
                        <span className="tiny muted">{a.companyName} · {shortDate(a.appliedAt)}</span>
                        <span className={b.cls}>{b.label}</span>
                      </div>
                    </div>
                  );
                })
              )}
            </section>
            <section className="card stack" style={{ gap: 10, background: "var(--brand-soft)", borderColor: "#cdd6f0" }}>
              <h4>Job alert</h4>
              <p className="small" style={{ color: "var(--brand-deep)" }}>Nhận thông báo khi có việc mới khớp kỹ năng và khu vực bạn quan tâm.</p>
              <Link to="/candidate/alerts" className="btn btn-p btn-sm" style={{ alignSelf: "flex-start" }}>Quản lý job alert</Link>
            </section>
          </aside>
        </section>
      </div>
      {applying ? <ApplyModal job={applying} onClose={() => setApplying(null)} onApplied={onApplied} /> : null}
    </>
  );
}
