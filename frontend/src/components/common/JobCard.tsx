import type { Job, MatchResult } from "../../types";
import { classNames, pct } from "../../utils/format";
import { Button } from "./Button";
import { Chip } from "./Chip";
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
      className={classNames("job-card", active && "active")}
      data-job-id={job.id}
      style={{ animationDelay: `${delayMs}ms` }}
      onClick={onClick}
    >
      <JobLogo initials={job.logo} color={job.logoColor} />
      <div>
        <h3>{job.title}</h3>
        <div className="job-meta">
          <span>{job.company}</span>
          <span>{job.location}</span>
          <span>{job.workType}</span>
          <span>{job.postedAgo}</span>
        </div>
        <div className="job-tags">
          {job.hot ? <Chip tone="hot">Hot</Chip> : null}
          {job.nearYou && job.distanceKm != null ? (
            <Chip tone="near">Cách bạn ~{job.distanceKm} km</Chip>
          ) : job.nearYou ? (
            <Chip tone="near">Gần bạn</Chip>
          ) : null}
          <Chip tone="brand">{job.level}</Chip>
          {job.requiredSkills.slice(0, 3).map((s) => (
            <Chip key={s}>{s}</Chip>
          ))}
        </div>
      </div>
      <div className="job-side">
        {showMatch && match ? (
          <div className="match-badge">{pct(match.score)}% phù hợp</div>
        ) : null}
        <div className="salary">{job.salary}</div>
        <Button
          variant="soft"
          size="sm"
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onApply?.(job.id);
          }}
        >
          Ứng tuyển
        </Button>
      </div>
    </article>
  );
}
