import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ApiError, applicationsApi, cvsApi, type CvFormDto } from "../../api/client";

/** Màn C05 · Modal ứng tuyển (design canvas ApplyModal.dc.html). */

const MAX_LETTER = 2000;

export interface ApplyTarget {
  id: string | number;
  title: string;
  company: string;
  location?: string;
  /** Điểm phù hợp 0–100 với CV hiện tại, nếu có. */
  matchPct?: number | null;
}

export function ApplyModal({
  job, onClose, onApplied,
}: {
  job: ApplyTarget;
  onClose: () => void;
  onApplied: () => void;
}) {
  const [cv, setCv] = useState<CvFormDto | null>(null);
  const [cvLoaded, setCvLoaded] = useState(false);
  const [letter, setLetter] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const letterRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    cvsApi.mine().then(setCv).catch(() => setCv(null)).finally(() => setCvLoaded(true));
    letterRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await applicationsApi.apply(Number(job.id), { coverLetter: letter.trim() || undefined });
      onApplied();
    } catch (err) {
      setError(err instanceof ApiError && err.status === 409
        ? "Bạn đã ứng tuyển tin này rồi. Xem trạng thái ở trang Đơn ứng tuyển."
        : err instanceof Error ? err.message : "Gửi đơn thất bại");
    } finally {
      setBusy(false);
    }
  }

  const cvName = cv?.profile?.personal_info?.full_name || cv?.fileName || "CV của bạn";
  const hasCv = !!cv?.fileName || !!cv?.analyzed;

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 50 }}>
      <div className="scrim" style={{ position: "fixed" }} onClick={onClose} />
      <div style={{ position: "absolute", inset: 0, display: "flex", justifyContent: "center", alignItems: "flex-start",
        padding: "80px 16px 24px", overflowY: "auto", pointerEvents: "none" }}>
        <form className="modal" role="dialog" aria-modal="true" aria-labelledby="apply-title" onSubmit={onSubmit}
          style={{ width: "min(620px, 100%)", display: "flex", flexDirection: "column", gap: 18, pointerEvents: "auto" }}>
          <div className="between" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>
            <div>
              <p className="kicker">Ứng tuyển</p>
              <h2 id="apply-title" style={{ fontSize: 24, marginTop: 4 }}>{job.title}</h2>
              <p className="small muted">{job.company}{job.location ? ` · ${job.location}` : ""}</p>
            </div>
            <button type="button" className="icon-btn" aria-label="Đóng" onClick={onClose}>×</button>
          </div>

          <fieldset style={{ border: 0, padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 8 }}>
            <legend className="lbl" style={{ marginBottom: 8 }}>CV gửi kèm</legend>
            {!cvLoaded ? (
              <p className="small muted">Đang tải CV…</p>
            ) : hasCv ? (
              <label style={{ display: "flex", gap: 14, alignItems: "center", padding: 14, borderRadius: 2,
                border: "2px solid var(--brand)", background: "#f5f7fd" }}>
                <input type="radio" name="cv" checked readOnly style={{ width: 18, height: 18, accentColor: "var(--brand)" }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontWeight: 650 }}>{cvName}</p>
                  <p className="tiny muted">CV chính{cv?.fileName ? ` · ${cv.fileName}` : ""}</p>
                </div>
                {job.matchPct != null ? <span className="match">{job.matchPct}%</span> : null}
              </label>
            ) : (
              <p className="note note-warn small">Bạn chưa có CV. Nhà tuyển dụng sẽ chỉ thấy thông tin tài khoản của bạn.</p>
            )}
            <Link to="/candidate/cv" className="small" style={{ color: "var(--brand)", fontWeight: 650 }}>
              {hasCv ? "+ Tải CV mới" : "+ Tải CV lên"}
            </Link>
          </fieldset>

          <div className="field">
            <label htmlFor="apply-letter">
              Thư giới thiệu <span className="muted" style={{ fontWeight: 400 }}>(không bắt buộc)</span>
            </label>
            <textarea id="apply-letter" ref={letterRef} className="input" style={{ minHeight: 140 }}
              maxLength={MAX_LETTER} value={letter} onChange={(e) => setLetter(e.target.value)}
              placeholder="Giới thiệu ngắn về kinh nghiệm và lý do bạn phù hợp với vị trí…" />
            <span className="help" style={{ textAlign: "right" }}>{letter.length} / {MAX_LETTER} ký tự</span>
          </div>

          {error ? <div className="note note-warn small" role="alert">{error}</div> : null}

          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button type="button" className="btn btn-g" onClick={onClose}>Huỷ</button>
            <button type="submit" className="btn btn-p" disabled={busy}>{busy ? "Đang gửi…" : "Gửi đơn ứng tuyển"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
