import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button, Can, EmptyNote, JobLogo, SiteHeader } from "../../components/common";
import { applicationsApi, jobsApi, matchingApi } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { mapJob, mapMatch } from "../../utils/mappers";
import { pct } from "../../utils/format";
import type { Job, MatchResult } from "../../types";

function pieces(text: string, splitCommas = false): string[] {
  const trimmed = text.trim();
  if (!trimmed) return [];
  const byLine = trimmed.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (byLine.length >= 2) return byLine;
  if (splitCommas) {
    const byComma = trimmed.split(",").map((part) => part.trim()).filter(Boolean);
    if (byComma.length >= 2) return byComma;
  }
  return [trimmed];
}

function TextBlock({ text, splitCommas = false }: { text: string; splitCommas?: boolean }) {
  const lines = pieces(text, splitCommas);
  if (lines.length >= 2) {
    return (
      <ul style={{ margin: 0, paddingLeft: 20, display: "grid", gap: 6, color: "var(--ink-soft)" }}>
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    );
  }
  return <p style={{ color: "var(--ink-soft)", whiteSpace: "pre-line" }}>{lines[0]}</p>;
}

export function CandidateJobDetailPage() {
  const { jobId } = useParams();
  const { can } = useAuth();
  const { toast } = useToast();
  const canReadMatch = can("matching:read-own");
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [match, setMatch] = useState<MatchResult | null>(null);

  useEffect(() => {
    const id = Number(jobId);
    if (!Number.isFinite(id)) {
      setLoading(false);
      return;
    }
    jobsApi
      .get(id)
      .then((dto) => setJob(mapJob(dto)))
      .catch((e) => toast(e instanceof Error ? e.message : "Không tải được tin tuyển dụng"))
      .finally(() => setLoading(false));
  }, [jobId, toast]);

  useEffect(() => {
    if (!canReadMatch) return;
    matchingApi
      .mine()
      .then((list) => setMatch(list.map(mapMatch).find((m) => m.jobId === String(jobId)) ?? null))
      .catch(() => setMatch(null));
  }, [jobId, canReadMatch]);

  const id = Number(jobId);

  async function apply() {
    try {
      await applicationsApi.apply(id);
      toast("Đã nộp hồ sơ ứng tuyển");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Ứng tuyển thất bại");
    }
  }

  const have = new Set((match?.matchedSkills ?? []).map((x) => x.toLowerCase()));
  const sections: { title: string; text: string; commas?: boolean }[] = job
    ? [
        { title: "Mô tả công việc", text: job.description },
        { title: "Yêu cầu", text: job.requirements, commas: true },
        { title: "Trách nhiệm", text: job.responsibilities, commas: true },
      ].filter((x) => x.text && x.text.trim())
    : [];

  return (
    <>
      <SiteHeader active="jobs" mode="candidate" />
      <div className="wrap" style={{ paddingTop: 20, paddingBottom: 64, display: "flex", flexDirection: "column", gap: 20 }}>
        <nav aria-label="Breadcrumb" className="small muted row" style={{ gap: 6 }}>
          <Link to="/candidate">Tổng quan</Link>
          <span>/</span>
          <Link to="/candidate/matching">Việc phù hợp</Link>
          <span>/</span>
          <span style={{ color: "var(--ink)" }}>{job?.title ?? "Chi tiết"}</span>
        </nav>

        {loading ? (
          <EmptyNote>Đang tải tin tuyển dụng…</EmptyNote>
        ) : !job ? (
          <EmptyNote>Không tìm thấy tin tuyển dụng này.</EmptyNote>
        ) : (
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "flex-start" }}>
            <main style={{ flex: "999 1 560px", minWidth: 0, display: "flex", flexDirection: "column", gap: 20 }}>
              <section className="card" style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16 }}>
                <div className="row" style={{ gap: 18, flexWrap: "nowrap", alignItems: "flex-start" }}>
                  <JobLogo initials={job.logo} className="logo-lg" />
                  <div style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: 6 }}>
                    <div className="row" style={{ gap: 8 }}>
                      {job.hot ? <span className="badge b-hot">HOT</span> : null}
                      <span className="tiny muted">{job.postedAgo}</span>
                    </div>
                    <h1 style={{ fontSize: 32 }}>{job.title}</h1>
                    <span style={{ color: "var(--brand)", fontWeight: 650 }}>{job.company}</span>
                  </div>
                </div>
                <p className="salary-hl" style={{ fontSize: 20 }}>{job.salary}</p>
                <div className="row" style={{ gap: "8px 20px", fontSize: 14, color: "var(--ink-soft)" }}>
                  {[job.location, job.workType, job.level, job.minYears > 0 ? `${job.minYears}+ năm` : "Không yêu cầu kinh nghiệm"]
                    .filter(Boolean)
                    .map((x) => <span key={x}>{x}</span>)}
                </div>
                <div className="row" style={{ gap: 10 }}>
                  <Can perm="application:apply">
                    <Button variant="primary" onClick={apply} style={{ flex: "1 1 260px" }}>Ứng tuyển ngay</Button>
                  </Can>
                  <Can perm="interview:practice">
                    <Button variant="ghost"
                      to={Number.isFinite(id) ? `/candidate/interview?jobId=${id}` : "/candidate/interview"}>
                      Luyện phỏng vấn cho tin này
                    </Button>
                  </Can>
                </div>
              </section>

              {match ? (
                <section className="card" style={{ padding: 24, display: "flex", gap: 24, flexWrap: "wrap", alignItems: "center",
                  background: "var(--brand-soft)", borderColor: "#cdd6f0" }}>
                  <div style={{ flex: "0 0 auto", textAlign: "center" }}>
                    <p className="disp" style={{ fontSize: 48, color: "var(--brand)" }}>{pct(match.score)}%</p>
                    <p className="small" style={{ color: "var(--brand-deep)", fontWeight: 600 }}>phù hợp với CV của bạn</p>
                  </div>
                  <div style={{ flex: "1 1 420px", display: "flex", flexDirection: "column", gap: 10 }}>
                    {[
                      ["Kỹ năng", match.skillOverlap],
                      ["Ngữ nghĩa", match.semanticSimilarity],
                    ].map(([n, v]) => (
                      <div key={n as string} style={{ display: "grid", gridTemplateColumns: "110px 1fr 44px", gap: 12, alignItems: "center", fontSize: 13.5 }}>
                        <span style={{ fontWeight: 600 }}>{n}</span>
                        <div className="meter"><span style={{ width: `${pct(v as number)}%` }} /></div>
                        <span style={{ textAlign: "right", fontWeight: 650 }}>{pct(v as number)}</span>
                      </div>
                    ))}
                    <p className="small" style={{ color: "var(--brand-deep)" }}>
                      {match.matchedSkills.length ? `Đã có: ${match.matchedSkills.join(", ")}` : ""}
                      {match.missingSkills.length ? (
                        <> · Còn thiếu: <strong>{match.missingSkills.join(", ")}</strong></>
                      ) : null}
                    </p>
                  </div>
                </section>
              ) : null}

              <article className="card" style={{ padding: 28, display: "flex", flexDirection: "column", gap: 22 }}>
                {sections.map((sec) => (
                  <section key={sec.title}>
                    <h3 style={{ marginBottom: 10 }}>{sec.title}</h3>
                    <TextBlock text={sec.text} splitCommas={sec.commas} />
                  </section>
                ))}
                {job.requiredSkills.length + job.preferredSkills.length > 0 ? (
                  <section>
                    <h3 style={{ marginBottom: 10 }}>Kỹ năng</h3>
                    <div className="row" style={{ gap: 6 }}>
                      {[...job.requiredSkills, ...job.preferredSkills].map((skill) => (
                        <span key={skill} className={have.has(skill.toLowerCase()) ? "tag tag-on" : "tag"}>{skill}</span>
                      ))}
                    </div>
                    {match ? <p className="help" style={{ marginTop: 8 }}>Kỹ năng tô màu là kỹ năng đã có trong CV của bạn.</p> : null}
                  </section>
                ) : null}
              </article>
            </main>

            <aside style={{ flex: "1 1 320px", minWidth: 0, maxWidth: 400, display: "flex", flexDirection: "column", gap: 20 }}>
              <section className="card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div className="row" style={{ gap: 12, flexWrap: "nowrap" }}>
                  <JobLogo initials={job.logo} />
                  <div><h4>{job.company}</h4><p className="small muted">{job.city}</p></div>
                </div>
                <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "110px 1fr", gap: "8px 12px", fontSize: 14 }}>
                  <dt className="muted">Mức lương</dt><dd style={{ margin: 0 }}>{job.salary}</dd>
                  <dt className="muted">Hình thức</dt><dd style={{ margin: 0 }}>{job.workType}</dd>
                  <dt className="muted">Cấp bậc</dt><dd style={{ margin: 0 }}>{job.level}</dd>
                  <dt className="muted">Kinh nghiệm</dt>
                  <dd style={{ margin: 0 }}>{job.minYears > 0 ? `từ ${job.minYears} năm` : "không yêu cầu"}</dd>
                  <dt className="muted">Địa điểm</dt><dd style={{ margin: 0 }}>{job.location}</dd>
                </dl>
              </section>
              <Link to="/candidate/matching" className="btn btn-g">← Quay lại việc phù hợp</Link>
            </aside>
          </div>
        )}
      </div>
    </>
  );
}
