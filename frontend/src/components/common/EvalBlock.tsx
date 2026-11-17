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
          <strong>Điểm / 10</strong>
          <div className="muted" style={{ fontSize: ".85rem" }}>
            {ev.modelVersion?.toLowerCase().includes("ai")
              ? "Chấm bởi HireLens AI"
              : "Theo tiêu chí đánh giá"}
          </div>
        </div>
      </div>
      <p className="muted">Điểm tổng kết hợp mức đạt tiêu chí và độ tương đồng với đáp án tham khảo.</p>
      <div className="muted">{ev.scoringMode === "bertscore" ? "BERTScore + rubric · điểm luyện tập tự động" : "Đối chiếu từ vựng + rubric"}</div>
      {ev.scoringMode === "bertscore" && <div>
        <EvalRow label="BERTScore Precision" value={ev.bertPrecision.toFixed(3)} />
        <EvalRow label="BERTScore Recall" value={ev.bertRecall.toFixed(3)} />
        <EvalRow label="BERTScore F1" value={ev.bertF1.toFixed(3)} />
      </div>}
      {ev.coverageScore != null && <EvalRow label="Độ phủ tiêu chí" value={`${Math.round(ev.coverageScore * 100)}%`} />}
      {ev.criterionResults?.map(c => <div key={c.key} className="eval-row">
        <div><strong>{c.label}</strong><p className="muted">{c.feedback}</p></div>
        <span>{c.points.toFixed(1)}/{c.max_points.toFixed(1)}</span>
      </div>)}
      <p style={{ margin: ".5rem 0 0" }}>{ev.comment}</p>
      <div className="job-tags" style={{ marginTop: ".5rem" }}>
        {ev.coveredPoints.map((p) => (
          <Chip key={`c-${p}`} tone="ok">
            {p}
          </Chip>
        ))}
        {ev.missingPoints.map((p) => (
          <Chip key={`m-${p}`} tone="warn">
            Cần bổ sung: {p}
          </Chip>
        ))}
      </div>
    </div>
  );
}
