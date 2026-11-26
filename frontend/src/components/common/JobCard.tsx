import type { Job, MatchResult } from "../../types";
import { classNames, pct } from "../../utils/format";
import { Button } from "./Button";
import { JobLogo } from "./JobLogo";

interface JobCardProps {
  job: Job;
  match?: MatchResult;
  showMatch?: boolean;
  active?: boolean;
  delayMs?: number;
  onClick?: () => void;
  onApply?: (jobId: string) => void;
}

export function JobCard({
  job,
  match,
  showMatch,
  active,
  delayMs = 0,
  onClick,
  onApply,
}: JobCardProps) {
  return (
    <article
      className={classNames("jobcard", active && "on")}
      data-job-id={job.id}
      style={{ animationDelay: `${delayMs}ms` }}
      onClick={onClick}
    >
      <JobLogo initials={job.logo} color={job.logoColor} />
      <div style={{ flex: "1 1 320px", minWidth: 0, display: "flex", flexDirection: "column", gap: 6 }}>
        <div className="row" style={{ gap: 8 }}>
          {job.hot ? <span className="badge b-hot">HOT</span> : null}
          {job.nearYou ? (
            <span className="badge b-brand b-plain">
              {job.distanceKm != null ? `Cách bạn ~${job.distanceKm} km` : "Gần bạn"}
            </span>
          ) : null}
          <span className="tiny muted">{job.postedAgo}</span>
        </div>
        <h3 className="jobcard-title">{job.title}</h3>
        <div className="row small muted" style={{ gap: "6px 14px" }}>
          <span style={{ fontWeight: 600, color: "var(--ink-soft)" }}>{job.company}</span>
          <span className="row" style={{ gap: 4 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z" />
              <circle cx="12" cy="9.5" r="2.5" />
            </svg>
            {job.location}
          </span>
          <span>{job.workType}</span>
          <span>{job.level}</span>
        </div>
        <div className="row" style={{ gap: 6, marginTop: 2 }}>
          {job.requiredSkills.slice(0, 4).map((s) => (
            <span key={s} className="tag">{s}</span>
          ))}
        </div>
      </div>
      <div className="jobcard-side">
        <span className="salary-hl">{job.salary}</span>
        {showMatch && match ? <span className="match">{pct(match.score)}% phù hợp</span> : null}
        {onApply ? (
          <Button
            variant="primary"
            size="sm"
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onApply(job.id);
            }}
          >
            Ứng tuyển
          </Button>
        ) : null}
      </div>
    </article>
  );
}
