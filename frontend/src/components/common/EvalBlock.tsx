import type { ReactNode } from "react";
import type { InterviewEvaluation } from "../../types";
import { Chip } from "./Chip";
import { ScoreRing } from "./ScoreRing";

interface EvalRowProps {
  label: ReactNode;
  value: ReactNode;
}

export function EvalRow({ label, value }: EvalRowProps) {
  return (
    <div className="eval-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

interface EvalBlockProps {
  evaluation: InterviewEvaluation;
}

export function EvalBlock({ evaluation: ev }: EvalBlockProps) {
  return (
    <div className="eval-block">
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "1rem",
          marginBottom: ".5rem",
        }}
      >
        <ScoreRing percent={Math.round(ev.predictedScore * 10)}>
          {ev.predictedScore.toFixed(1)}
        </ScoreRing>
        <div>
          <strong>Điểm dự đoán / 10</strong>
          <div className="muted" style={{ fontSize: ".85rem" }}>
            {ev.scoreScale}
          </div>
        </div>
      </div>
      <EvalRow label="BERTScore P" value={ev.bertPrecision.toFixed(3)} />
      <EvalRow label="BERTScore R" value={ev.bertRecall.toFixed(3)} />
      <EvalRow label="BERTScore F1" value={ev.bertF1.toFixed(3)} />
      <p style={{ margin: ".5rem 0 0" }}>{ev.comment}</p>
      <div>
        {ev.coveredPoints.map((p) => (
          <Chip key={`c-${p}`} tone="ok">
            {p}
          </Chip>
        ))}
        {ev.missingPoints.map((p) => (
          <Chip key={`m-${p}`} tone="warn">
            Thiếu: {p}
          </Chip>
        ))}
      </div>
      <p className="hint">Model: {ev.modelVersion}</p>
    </div>
  );
}
