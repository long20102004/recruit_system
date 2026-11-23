import { useState } from "react";
import { matchingApi, type ExplanationDto, type MatchBand } from "../../api/client";
import { Button } from "./Button";
import { Chip } from "./Chip";

const BAND_LABEL: Record<MatchBand, string> = {
  high: "Phù hợp cao",
  mid: "Cân nhắc",
  low: "Phù hợp thấp",
};
const BAND_TONE: Record<MatchBand, "ok" | "near" | "warn"> = {
  high: "ok",
  mid: "near",
  low: "warn",
};

/** Nhãn mức khớp của cvmatch (high / mid / low). */
export function BandBadge({ band }: { band: MatchBand }) {
  return <Chip tone={BAND_TONE[band]}>{BAND_LABEL[band]}</Chip>;
}

interface MatchExplainProps {
  matchId?: number;
  /** false: kết quả của engine cũ, không có giải thích chi tiết. */
  available?: boolean;
}

/** Nút "Vì sao?" + nội dung giải thích (lấy lười một lần, server lưu lại). */
export function MatchExplain({ matchId, available = true }: MatchExplainProps) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<ExplanationDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!matchId || !available) return null;

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (!next || data || loading) return;
    setLoading(true);
    setError(null);
    try {
      setData(await matchingApi.explanation(matchId as number));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải được giải thích");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="match-explain">
      <Button variant="ghost" size="sm" onClick={toggle}>
        {open ? "Ẩn giải thích" : "Vì sao?"}
      </Button>
      {open ? (
        <div className="match-explain-body muted" style={{ whiteSpace: "pre-wrap", marginTop: ".5rem" }}>
          {loading ? "Đang tải giải thích…" : error ? error : data?.text}
        </div>
      ) : null}
    </div>
  );
}
