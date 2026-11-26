import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import type { Job, MatchResult } from "../../types";
import { pct } from "../../utils/format";
import { Button } from "./Button";
import { BandBadge, MatchExplain } from "./MatchExplain";

interface MatchItemProps {
  job: Job;
  match: MatchResult;
  actionHref?: string;
  actionLabel?: string;
}

function gapLine(match: MatchResult): string {
  const gaps: string[] = [];
  if (match.missingSkills.length > 0) {
    gaps.push("thiếu " + match.missingSkills.join(", "));
  }
  if (match.partialSkills && match.partialSkills.length > 0) {
    gaps.push("mới gần đúng " + match.partialSkills.join(", "));
  }
  // engine cũ: lý do dạng câu; cvmatch: chi tiết nằm trong "Vì sao?"
  const lowExperience = match.band
    ? undefined
    : match.reasons.find((reason) => /thấp hơn/i.test(reason));
  if (lowExperience) {
    gaps.push(lowExperience.charAt(0).toLowerCase() + lowExperience.slice(1));
  }
  if (gaps.length === 0) {
    return "Đã phù hợp với yêu cầu kỹ năng và kinh nghiệm đang so khớp.";
  }
  return "Chưa phù hợp: " + gaps.join("; ") + ".";
}

export function MatchItem({
  job,
  match,
  actionHref = "/candidate/matching",
  actionLabel = "Xem chi tiết",
}: MatchItemProps) {
  const parts: [string, number][] = match.band
    ? []
    : [
        ["Kỹ năng", match.skillOverlap],
        ["Ngữ nghĩa", match.semanticSimilarity],
        ["Từ khoá", match.tfidfSimilarity],
      ];
  return (
    <article className="card" style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "flex-start" }}>
      <div style={{ flex: "0 0 96px", textAlign: "center", paddingTop: 4 }}>
        {match.band ? (
          // cvmatch: ứng viên thấy mức khớp, không thấy điểm (plan Q-B)
          <BandBadge band={match.band} />
        ) : (
          <>
            <p className="disp" style={{ fontSize: 36, color: "var(--brand)" }}>{pct(match.score)}%</p>
            <p className="tiny muted">phù hợp</p>
          </>
        )}
        {match.rank ? <p className="tiny muted" style={{ marginTop: 6 }}>Hạng #{match.rank}</p> : null}
      </div>
      <div style={{ flex: "1 1 380px", minWidth: 0, display: "flex", flexDirection: "column", gap: 8 }}>
        <Link to={actionHref} className="disp" style={{ fontSize: 20 }}>{job.title}</Link>
        <p className="small muted">{job.company} · {job.location} · {job.salary}</p>
        {parts.length ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12, marginTop: 4 }}>
            {parts.map(([n, v]) => (
              <div key={n}>
                <div className="between tiny" style={{ marginBottom: 4 }}>
                  <span className="muted">{n}</span>
                  <strong>{pct(v)}%</strong>
                </div>
                <div className="meter"><span style={{ width: `${pct(v)}%` }} /></div>
              </div>
            ))}
          </div>
        ) : null}
        <p className="small">
          {match.matchedSkills.length ? (
            <span style={{ color: "var(--ok)", fontWeight: 600 }}>Có: {match.matchedSkills.join(", ")}</span>
          ) : null}
          {match.matchedSkills.length && match.missingSkills.length ? " · " : null}
          {match.missingSkills.length ? (
            <span style={{ color: "var(--warn)", fontWeight: 600 }}>Thiếu: {match.missingSkills.join(", ")}</span>
          ) : null}
        </p>
        <p className="help">{gapLine(match)}</p>
        {match.capApplied ? (
          <p className="help">Mức phù hợp bị giới hạn vì CV chưa thể hiện kỹ năng bắt buộc.</p>
        ) : null}
        <MatchExplain matchId={match.id} available={Boolean(match.band)} />
      </div>
      <div style={{ flex: "0 0 auto", display: "flex", flexDirection: "column", gap: 8 }}>
        <Button variant="primary" size="sm" to={actionHref}>{actionLabel}</Button>
        <Button variant="ghost" size="sm" to={`/candidate/interview?jobId=${job.id}`}>Luyện phỏng vấn</Button>
      </div>
    </article>
  );
}

interface MatchBadgeProps {
  children: ReactNode;
}

export function MatchBadge({ children }: MatchBadgeProps) {
  return <div className="match-badge">{children}</div>;
}
