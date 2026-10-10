import type { ReactNode } from "react";
import type { Job, MatchResult } from "../../types";
import { pct } from "../../utils/format";
import { Button } from "./Button";
import { Chip } from "./Chip";
import { JobLogo } from "./JobLogo";
import { ProgressBar } from "./ProgressBar";
import { ScoreRing } from "./ScoreRing";

interface MatchItemProps {
  job: Job;
  match: MatchResult;
  actionHref?: string;
  actionLabel?: string;
}

export function MatchItem({
  job,
  match,
  actionHref = "/candidate/interview",
  actionLabel = "Phỏng vấn",
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
        <div>
          {match.matchedSkills.map((s) => (
            <Chip key={`m-${s}`} tone="ok">
              {s}
            </Chip>
          ))}
          {match.missingSkills.map((s) => (
            <Chip key={`x-${s}`} tone="warn">
              Thiếu: {s}
            </Chip>
          ))}
        </div>
        <ul
          style={{
            margin: ".75rem 0 0",
            paddingLeft: "1.1rem",
            color: "var(--muted)",
          }}
        >
          {match.reasons.map((x) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
        <p className="hint">
          Semantic: {pct(match.semanticSimilarity)}% · TF-IDF:{" "}
          {pct(match.tfidfSimilarity)}% · Model: {match.modelVersion}
        </p>
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
