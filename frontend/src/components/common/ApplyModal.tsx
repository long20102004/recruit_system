import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ApiError, MAX_CANDIDATE_CVS, applicationsApi, cvsApi, type CvDocumentDto } from "../../api/client";

/** Màn C05 · Modal ứng tuyển (design canvas ApplyModal.dc.html). */

const MAX_LETTER = 2000;

export interface ApplyTarget {
  id: string | number;
  title: string;
  company: string;
  location?: string;
  /** Điểm phù hợp 0–100 với CV chính, nếu có (chỉ CV chính được chấm điểm). */
  matchPct?: number | null;
}

export function ApplyModal({
  job, onClose, onApplied,
}: {
  job: ApplyTarget;
  onClose: () => void;
  onApplied: () => void;
}) {
  const [cvs, setCvs] = useState<CvDocumentDto[]>([]);
  const [cvId, setCvId] = useState<number | null>(null);
  const [cvLoaded, setCvLoaded] = useState(false);
  const [letter, setLetter] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const letterRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    cvsApi.documents()
      .then((list) => {
        // analyzed = đã có nội dung (CV upload đã trích xuất, hoặc CV tạo từ form/mẫu đã lưu).
        const ready = list.filter((c) => c.analyzed);
        setCvs(ready);
        setCvId((ready.find((c) => c.main) ?? ready[0])?.id ?? null);
      })
      .catch(() => setCvs([]))
      .finally(() => setCvLoaded(true));
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
      await applicationsApi.apply(Number(job.id), {
        cvDocumentId: cvId ?? undefined,
        coverLetter: letter.trim() || undefined,
      });
      onApplied();
    } catch (err) {
      setError(err instanceof ApiError && err.status === 409
        ? "Bạn đã ứng tuyển tin này rồi. Xem trạng thái ở trang Đơn ứng tuyển."
        : err instanceof Error ? err.message : "Gửi đơn thất bại");
    } finally {
      setBusy(false);
    }
  }

  const hasCv = cvs.length > 0;

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
              cvs.map((c) => {
                const selected = c.id === cvId;
                return (
                  <label key={c.id} style={{ display: "flex", gap: 14, alignItems: "center", padding: 14, borderRadius: 2,
                    border: selected ? "2px solid var(--brand)" : "1px solid var(--line)",
                    background: selected ? "#f5f7fd" : undefined, cursor: "pointer" }}>
                    <input type="radio" name="cv" checked={selected} onChange={() => setCvId(c.id)}
                      style={{ width: 18, height: 18, accentColor: "var(--brand)" }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontWeight: 650 }}>{c.title}</p>
                      <p className="tiny muted">
                        {c.main ? "CV chính" : "CV phụ"}{c.fileName ? ` · ${c.fileName}` : " · Tạo từ mẫu"}
                      </p>
                    </div>
                    {c.main && job.matchPct != null ? <span className="match">{job.matchPct}%</span> : null}
                  </label>
                );
              })
            ) : (
              <p className="note note-warn small">Bạn chưa có CV. Nhà tuyển dụng sẽ chỉ thấy thông tin tài khoản của bạn.</p>
            )}
            {cvs.length < MAX_CANDIDATE_CVS ? (
              <Link to="/candidate/cv?new=1" className="small" style={{ color: "var(--brand)", fontWeight: 650 }}>
                {hasCv ? "+ Tải CV mới" : "+ Tải CV lên"}
              </Link>
            ) : null}
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
