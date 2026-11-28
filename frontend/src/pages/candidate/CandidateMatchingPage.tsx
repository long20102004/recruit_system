import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ApplyModal,
  Button,
  EmptyNote,
  MatchItem,
  SiteHeader,
  type ApplyTarget,
} from "../../components/common";
import { useAuth } from "../../context/AuthContext";
import {
  accountApi,
  MAX_PAGE_SIZE,
  cvsApi,
  jobsApi,
  matchingApi,
  type JobDto,
  type MatchDto,
} from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { mapJob, mapMatch } from "../../utils/mappers";

export function CandidateMatchingPage() {
  const { toast } = useToast();
  const [alertCutoff] = useState(() => Date.now() - 7 * 86_400_000);
  const [alertsEnabled, setAlertsEnabled] = useState(false);
  const [matches, setMatches] = useState<MatchDto[]>([]);
  const [jobs, setJobs] = useState<JobDto[]>([]);
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [applying, setApplying] = useState<ApplyTarget | null>(null);
  const { can } = useAuth();
  const [scoreError, setScoreError] = useState<string | null>(null);

  const load = useCallback(async (refresh = false) => {
    const form = await cvsApi.mine();
    const analyzed = form.analyzed;
    setReady(analyzed);
    if (!analyzed) {
      setMatches([]);
      setJobs([]);
      setScoreError(null);
      return "empty" as const;
    }
    const jobList = (await jobsApi.list({ size: MAX_PAGE_SIZE })).content;
    setJobs(jobList);
    let stored: MatchDto[] = [];
    try {
      stored = (await matchingApi.mine({ size: MAX_PAGE_SIZE })).content;
    } catch {
      stored = [];
    }
    setMatches(stored);
    if (!refresh) {
      setScoreError(null);
      return stored.length ? "stored" as const : "listed" as const;
    }
    try {
      setMatches(await matchingApi.refreshMine());
      setScoreError(null);
      return "scored" as const;
    } catch (e) {
      const message = e instanceof Error ? e.message : "Không chấm được mức phù hợp";
      setScoreError(stored.length > 0 ? null : message);
      if (stored.length === 0 && jobList.length === 0) throw e;
      return stored.length > 0 ? ("stored" as const) : ("listed" as const);
    }
  }, []);

  useEffect(() => {
    load()
      .catch((e) => toast(e instanceof Error ? e.message : "Không tải được việc phù hợp"))
      .finally(() => setLoading(false));
  }, [load, toast]);

  useEffect(() => {
    let active = true;
    accountApi.notifications().then(({ items }) => {
      if (active) setAlertsEnabled(items.find((item) => item.type === "JOB_ALERT")?.inApp ?? true);
    }).catch(() => { if (active) setAlertsEnabled(false); });
    return () => { active = false; };
  }, []);

  async function rematch() {
    setBusy(true);
    try {
      const result = await load(true);
      if (result === "scored") toast("Đã cập nhật việc phù hợp theo CV");
      else if (result === "stored") toast("Giữ điểm đã lưu. Service chấm điểm đang không chạy.");
      else toast("Đã hiện tin tuyển dụng. Service chấm điểm đang không chạy.");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không cập nhật được danh sách");
    } finally {
      setBusy(false);
    }
  }

  const ranked = [...matches].sort(
    (a, b) => Number(b.overallScore) - Number(a.overallScore)
  );

  const jobsById = new Map(jobs.map((job) => [job.id, job]));
  const alerts = alertsEnabled ? ranked.flatMap((match) => {
    const job = jobsById.get(match.jobId);
    const published = job?.postedAt ? Date.parse(job.postedAt) : 0;
    return job && Number(match.overallScore) >= 0.8 && published >= alertCutoff
      ? [{ job, score: Number(match.overallScore) }] : [];
  }).slice(0, 5) : [];

  const [band, setBand] = useState<"all" | "high" | "mid">("all");
  const high = ranked.filter((r) => Number(r.overallScore) >= 0.8).length;
  const shown = ranked.filter((r) => {
    const v = Number(r.overallScore);
    return band === "all" || (band === "high" ? v >= 0.8 : v >= 0.6 && v < 0.8);
  });

  return (
    <>
      <SiteHeader active="matching" mode="candidate" />
      <div className="wrap" style={{ paddingTop: 32, paddingBottom: 64, display: "flex", flexDirection: "column", gap: 22 }}>
        <div className="page-head" style={{ marginBottom: 0 }}>
          <div>
            <p className="kicker">Gợi ý việc làm bằng AI</p>
            <h1 style={{ fontSize: 34, marginTop: 6 }}>Việc phù hợp với CV của bạn</h1>
          </div>
          {ready ? (
            <button type="button" className="btn btn-g" onClick={rematch} disabled={busy}>
              {busy ? "Đang tính lại…" : "Tính lại"}
            </button>
          ) : null}
        </div>

        <section className="card" style={{ display: "flex", gap: 28, flexWrap: "wrap", alignItems: "center",
          background: "var(--brand-soft)", borderColor: "#cdd6f0" }}>
          <div style={{ flex: "1 1 320px", display: "flex", flexDirection: "column", gap: 6 }}>
            <h3>Cách tính điểm phù hợp</h3>
            <p className="small" style={{ color: "var(--brand-deep)" }}>
              So khớp kỹ năng, kinh nghiệm và nội dung CV với từng tin đang mở. Bấm “Tính lại” sau khi sửa CV.
            </p>
          </div>
          <div className="row" style={{ gap: 24 }}>
            <div><p className="disp" style={{ fontSize: 28, color: "var(--brand)" }}>{ranked.length}</p><p className="tiny" style={{ color: "var(--brand-deep)" }}>tin đã chấm</p></div>
            <div><p className="disp" style={{ fontSize: 28, color: "var(--brand)" }}>{high}</p><p className="tiny" style={{ color: "var(--brand-deep)" }}>tin trên 80%</p></div>
          </div>
        </section>

        {alerts.length > 0 && (
          <section className="card stack">
            <h2 style={{ fontSize: 18 }}>Việc mới phù hợp trong 7 ngày qua</h2>
            {alerts.map(({ job, score }) => (
              <Link key={job.id} to={`/candidate/jobs/${job.id}`}>{job.title} · {Math.round(score * 100)}%</Link>
            ))}
          </section>
        )}

        {ready && ranked.length > 0 ? (
          <div className="row" style={{ gap: 8 }}>
            {([["all", "Tất cả"], ["high", "Trên 80%"], ["mid", "60 – 80%"]] as const).map(([k, label]) => (
              <button key={k} type="button" className={band === k ? "tag tag-on" : "tag"} onClick={() => setBand(k)}>
                {label}
              </button>
            ))}
          </div>
        ) : null}

        <section style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {loading ? (
            <EmptyNote>Đang kiểm tra hồ sơ…</EmptyNote>
          ) : !ready ? (
            <div className="note note-warn small">
              Bạn chưa có CV đã phân tích. Tải CV lên để xem việc phù hợp.{" "}
              <Link to="/candidate/cv" style={{ fontWeight: 700, textDecoration: "underline" }}>Tải CV</Link>
            </div>
          ) : ranked.length === 0 && jobs.length === 0 ? (
            <EmptyNote>CV đã được phân tích nhưng chưa có tin tuyển dụng để so khớp.</EmptyNote>
          ) : ranked.length === 0 ? (
            <>
              <div className="note small">
                {scoreError
                  ? `Chưa chấm được mức phù hợp (${scoreError}). Các tin đang mở:`
                  : "Chưa có điểm phù hợp. Các tin đang mở:"}
              </div>
              {jobs.map((job) => {
                const mapped = mapJob(job);
                return (
                  <article key={job.id} className="card between">
                    <div style={{ minWidth: 0 }}>
                      <h3>{mapped.title}</h3>
                      <p className="small muted">{mapped.company} · {mapped.location} · {mapped.salary}</p>
                      <p className="help" style={{ marginTop: 6 }}>
                        Kỹ năng yêu cầu: {mapped.requiredSkills.join(", ") || "Chưa khai báo"}
                      </p>
                    </div>
                    <Button variant="ghost" size="sm" to={`/candidate/jobs/${job.id}`}>Xem chi tiết</Button>
                  </article>
                );
              })}
            </>
          ) : shown.length === 0 ? (
            <EmptyNote>Không có tin trong khoảng điểm này.</EmptyNote>
          ) : (
            shown.map((r, idx) => {
              const job = jobs.find((j) => j.id === r.jobId);
              if (!job) return null;
              const mapped = mapJob(job);
              const match = mapMatch(r);
              if (!match.rank) match.rank = idx + 1;
              return (
                <MatchItem key={r.id} job={mapped} match={match}
                  actionHref={`/candidate/jobs/${job.id}`} actionLabel="Xem chi tiết"
                  onApply={can("application:apply") ? () => setApplying({ id: job.id, title: mapped.title,
                    company: mapped.company, location: mapped.location, matchPct: Math.round(Number(r.overallScore) * 100) }) : undefined} />
              );
            })
          )}
        </section>
      </div>
      {applying ? (
        <ApplyModal job={applying} onClose={() => setApplying(null)}
          onApplied={() => { setApplying(null); toast("Đã gửi đơn. Nhà tuyển dụng sẽ nhận được thông báo."); }} />
      ) : null}
    </>
  );
}
