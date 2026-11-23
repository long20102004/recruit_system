import type { ReactNode } from "react";
import type { Job, MatchResult } from "../../types";
import { pct } from "../../utils/format";
import { Button } from "./Button";
import { JobLogo } from "./JobLogo";
import { ProgressBar } from "./ProgressBar";
import { ScoreRing } from "./ScoreRing";

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
  const lowExperience = match.reasons.find((reason) => /thấp hơn/i.test(reason));
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
  return (
    <article className="match-item">
      <div>
        <div
          style={{
            display: "flex",
            gap: ".5rem",
            alignItems: "center",
            marginBottom: ".35rem",
          }}
        >
          <JobLogo
            initials={job.logo}
            color={job.logoColor}
            style={{ width: 40, height: 40, fontSize: ".8rem" }}
          />
          <div>
            <h3 style={{ margin: 0 }}>
              #{match.rank} · {job.title}
            </h3>
            <div className="muted">
              {job.company} · {job.location} · {job.salary}
            </div>
          </div>
        </div>
        <ProgressBar percent={pct(match.score)} />
        <p className="match-gap">{gapLine(match)}</p>
      </div>
      <div style={{ textAlign: "center" }}>
        <ScoreRing percent={pct(match.score)}>
          {pct(match.score)}
        </ScoreRing>
        <Button
          variant="accent"
          size="sm"
          to={actionHref}
          style={{ marginTop: ".75rem" }}
        >
          {actionLabel}
        </Button>
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
