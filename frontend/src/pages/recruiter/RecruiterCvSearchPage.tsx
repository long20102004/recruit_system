import { useEffect, useMemo, useState, type FormEvent } from "react";
import { EmptyNote, MockNote, RecruiterLayout } from "../../components/common";
import {
  CV_COMPARE_JOBS,
  listCandidateCvs,
  toggleSaveCv,
  updateCvNote,
  type CvCandidateSummary,
} from "../../api/mock/recruiterMock";
import { useToast } from "../../context/ToastContext";

type CvTab = "search" | "saved";
type ExpFilter = "all" | "under2" | "2to5" | "over5";

const CITY_OPTIONS = ["Tất cả thành phố", "TP. Hồ Chí Minh", "Hà Nội", "Đà Nẵng"] as const;

export function RecruiterCvSearchPage() {
  const { toast } = useToast();
  const [cvs, setCvs] = useState<CvCandidateSummary[] | null>(null);
  const [tab, setTab] = useState<CvTab>("search");

  const [keywordDraft, setKeywordDraft] = useState("");
  const [cityDraft, setCityDraft] = useState<string>("Tất cả thành phố");
  const [expDraft, setExpDraft] = useState<ExpFilter>("all");

  const [appliedKeyword, setAppliedKeyword] = useState("");
  const [appliedCity, setAppliedCity] = useState<string>("Tất cả thành phố");
  const [appliedExp, setAppliedExp] = useState<ExpFilter>("all");
  const [compareJob, setCompareJob] = useState<string>(CV_COMPARE_JOBS[0]);

  const [viewingCv, setViewingCv] = useState<CvCandidateSummary | null>(null);
  const [savingTarget, setSavingTarget] = useState<CvCandidateSummary | null>(null);
  const [noteInput, setNoteInput] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listCandidateCvs()
      .then(setCvs)
      .catch((e) => {
        setCvs([]);
        toast(e instanceof Error ? e.message : "Không tải được danh sách CV");
      });
  }, [toast]);

  const savedCount = useMemo(
    () => (cvs ?? []).filter((c) => c.saved).length,
    [cvs]
  );

  const filtered = useMemo(() => {
    const needle = appliedKeyword.trim().toLowerCase();
    return (cvs ?? [])
      .filter((c) => {
        if (tab === "saved" && !c.saved) return false;
        if (appliedCity !== "Tất cả thành phố" && c.city !== appliedCity) return false;
        if (appliedExp === "under2" && c.yearsExp >= 2) return false;
        if (appliedExp === "2to5" && (c.yearsExp < 2 || c.yearsExp > 5)) return false;
        if (appliedExp === "over5" && c.yearsExp <= 5) return false;
        if (needle) {
          const hay = [c.code, c.title, c.city, ...c.skills].join(" ").toLowerCase();
          const tokens = needle.split(/\s+/).filter(Boolean);
          if (!tokens.every((t) => hay.includes(t))) return false;
        }
        return true;
      })
      .sort((a, b) => {
        const sa = a.matchByJob[compareJob] ?? 0;
        const sb = b.matchByJob[compareJob] ?? 0;
        return sb - sa;
      });
  }, [cvs, tab, appliedKeyword, appliedCity, appliedExp, compareJob]);

  function handleSearchSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setAppliedKeyword(keywordDraft);
    setAppliedCity(cityDraft);
    setAppliedExp(expDraft);
  }

  function handleResetFilters() {
    setKeywordDraft("");
    setCityDraft("Tất cả thành phố");
    setExpDraft("all");
    setAppliedKeyword("");
    setAppliedCity("Tất cả thành phố");
    setAppliedExp("all");
  }

  function openSaveDialog(c: CvCandidateSummary) {
    setSavingTarget(c);
    setNoteInput(c.note);
  }

  async function handleConfirmSave(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!savingTarget) return;
    setBusy(true);
    try {
      const updated = savingTarget.saved
        ? await updateCvNote(savingTarget.id, noteInput)
        : await toggleSaveCv(savingTarget.id, true, noteInput);
      setCvs((prev) => (prev ?? []).map((x) => (x.id === updated.id ? updated : x)));
      if (viewingCv?.id === updated.id) setViewingCv(updated);
      toast(savingTarget.saved ? "Đã cập nhật ghi chú CV." : `Đã lưu ${updated.code}.`);
      setSavingTarget(null);
      setNoteInput("");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Lưu CV thất bại");
    } finally {
      setBusy(false);
    }
  }

  async function handleUnsave(c: CvCandidateSummary) {
    try {
      const updated = await toggleSaveCv(c.id, false);
      setCvs((prev) => (prev ?? []).map((x) => (x.id === updated.id ? updated : x)));
      if (viewingCv?.id === updated.id) setViewingCv(updated);
      toast(`Đã bỏ lưu ${updated.code}.`);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Bỏ lưu thất bại");
    }
  }

  return (
    <RecruiterLayout active="cvSearch">
      <MockNote />

      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1 style={{ fontSize: 32 }}>Tìm &amp; lưu CV</h1>
          <p className="muted">
            Chỉ hiển thị ứng viên bật “Đang tìm việc”. Thông tin liên hệ ẩn cho đến khi ứng viên ứng tuyển.
          </p>
        </div>
      </div>

      <div className="tabs" role="tablist" aria-label="Chế độ xem CV">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "search"}
          className={tab === "search" ? "tab tab-on" : "tab"}
          onClick={() => setTab("search")}
        >
          Tìm CV
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "saved"}
          className={tab === "saved" ? "tab tab-on" : "tab"}
          onClick={() => setTab("saved")}
        >
          CV đã lưu
          <span className="count">{savedCount}</span>
        </button>
      </div>

      <form className="search" role="search" onSubmit={handleSearchSubmit}>
        <label className="seg" style={{ flex: "3 1 300px" }}>
          <input
            type="search"
            placeholder="Kỹ năng, chức danh (VD: Java Spring Boot)"
            aria-label="Kỹ năng, chức danh"
            value={keywordDraft}
            onChange={(e) => setKeywordDraft(e.target.value)}
          />
        </label>
        <label className="seg" style={{ flex: "1 1 160px" }}>
          <select
            aria-label="Thành phố"
            value={cityDraft}
            onChange={(e) => {
              setCityDraft(e.target.value);
              setAppliedCity(e.target.value);
            }}
          >
            {CITY_OPTIONS.map((city) => (
              <option key={city} value={city}>
                {city}
              </option>
            ))}
          </select>
        </label>
        <label className="seg" style={{ flex: "1 1 160px" }}>
          <select
            aria-label="Kinh nghiệm"
            value={expDraft}
            onChange={(e) => {
              const val = e.target.value as ExpFilter;
              setExpDraft(val);
              setAppliedExp(val);
            }}
          >
            <option value="all">Mọi kinh nghiệm</option>
            <option value="under2">Dưới 2 năm</option>
            <option value="2to5">2 – 5 năm</option>
            <option value="over5">Trên 5 năm</option>
          </select>
        </label>
        <button type="submit" className="btn btn-p">
          Tìm
        </button>
      </form>

      <div className="row">
        <label className="row small" style={{ gap: 8 }}>
          <span className="muted">So với tin</span>
          <select
            className="input"
            aria-label="So với tin tuyển dụng"
            style={{ height: 38, width: "auto" }}
            value={compareJob}
            onChange={(e) => setCompareJob(e.target.value)}
          >
            {CV_COMPARE_JOBS.map((job) => (
              <option key={job} value={job}>
                {job}
              </option>
            ))}
          </select>
        </label>
        <span className="small muted" style={{ marginLeft: "auto" }}>
          {filtered.length} CV phù hợp
        </span>
      </div>

      {cvs === null ? (
        <p className="muted">Đang tải hồ sơ ứng viên…</p>
      ) : filtered.length === 0 ? (
        <EmptyNote>
          <p>
            {tab === "saved"
              ? "Chưa có CV đã lưu nào khớp bộ lọc."
              : "Không tìm thấy CV phù hợp với tiêu chí hiện tại."}
          </p>
          <button
            type="button"
            className="btn btn-g btn-sm"
            style={{ marginTop: 12 }}
            onClick={handleResetFilters}
          >
            Xoá bộ lọc
          </button>
        </EmptyNote>
      ) : (
        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 380px), 1fr))",
            gap: 14,
          }}
        >
          {filtered.map((c) => {
            const score = c.matchByJob[compareJob] ?? 0;
            return (
              <article key={c.id} className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div className="row" style={{ gap: 12, flexWrap: "nowrap" }}>
                  <span className="avatar">ỨV</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontWeight: 650 }}>{c.code}</p>
                    <p className="tiny muted">
                      {c.title} · {c.expLabel} · {c.city}
                    </p>
                  </div>
                  {compareJob !== "Không so sánh" ? <span className="match">{score}%</span> : null}
                </div>

                <div className="row" style={{ gap: 6 }}>
                  {c.skills.map((s) => (
                    <span key={s} className="tag">
                      {s}
                    </span>
                  ))}
                </div>

                {c.saved && c.note ? (
                  <p
                    className="small"
                    style={{ background: "var(--gold-soft)", color: "var(--gold)", padding: "8px 10px" }}
                  >
                    <strong>Ghi chú:</strong> {c.note}
                  </p>
                ) : null}

                <div
                  className="row"
                  style={{ gap: 8, borderTop: "1px solid var(--line)", paddingTop: 12, marginTop: "auto" }}
                >
                  <button
                    type="button"
                    className="btn btn-g btn-sm"
                    onClick={() => setViewingCv(c)}
                  >
                    Xem CV
                  </button>
                  {c.saved ? (
                    <>
                      <button
                        type="button"
                        className="btn btn-g btn-sm"
                        onClick={() => openSaveDialog(c)}
                      >
                        Sửa ghi chú
                      </button>
                      <button
                        type="button"
                        className="btn btn-d btn-sm"
                        onClick={() => void handleUnsave(c)}
                      >
                        Bỏ lưu
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-g btn-sm"
                      onClick={() => openSaveDialog(c)}
                    >
                      Lưu CV
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </section>
      )}

      {viewingCv ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="cv-preview-title"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 50,
            display: "grid",
            placeItems: "center",
            padding: 20,
          }}
        >
          <div className="scrim" onClick={() => setViewingCv(null)} />
          <div className="modal stack" style={{ gap: 16, maxHeight: "90vh", overflowY: "auto" }}>
            <div className="between">
              <div>
                <h2 id="cv-preview-title" style={{ fontSize: 22 }}>
                  {viewingCv.code}
                </h2>
                <p className="small muted">
                  {viewingCv.title} · {viewingCv.expLabel} · {viewingCv.city}
                </p>
              </div>
              <button type="button" className="btn btn-g btn-sm" onClick={() => setViewingCv(null)}>
                Đóng
              </button>
            </div>

            <p className="note small">
              Thông tin liên hệ (họ tên thật, email, SĐT) được ẩn cho đến khi ứng viên nộp đơn vào tin của công ty.
            </p>

            <div>
              <p className="kicker" style={{ color: "var(--muted)" }}>
                Tóm tắt
              </p>
              <p className="small" style={{ marginTop: 6, color: "var(--ink-soft)" }}>
                {viewingCv.summary}
              </p>
            </div>

            <div>
              <p className="kicker" style={{ color: "var(--muted)" }}>
                Kinh nghiệm
              </p>
              <div className="stack" style={{ gap: 10, marginTop: 8 }}>
                {viewingCv.experiences.map((exp) => (
                  <div key={`${exp.role}-${exp.company}`} style={{ borderTop: "1px solid var(--line)", paddingTop: 8 }}>
                    <div className="between">
                      <p style={{ fontWeight: 650 }}>
                        {exp.role} · {exp.company}
                      </p>
                      <span className="tiny muted">{exp.period}</span>
                    </div>
                    <p className="small" style={{ color: "var(--ink-soft)", marginTop: 4 }}>
                      {exp.summary}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <p className="kicker" style={{ color: "var(--muted)" }}>
                Học vấn
              </p>
              <p className="small" style={{ marginTop: 6 }}>
                {viewingCv.education}
              </p>
            </div>

            <div>
              <p className="kicker" style={{ color: "var(--muted)" }}>
                Kỹ năng
              </p>
              <div className="row" style={{ gap: 6, marginTop: 8 }}>
                {viewingCv.skills.map((s) => (
                  <span key={s} className="tag tag-on">
                    {s}
                  </span>
                ))}
              </div>
            </div>

            <div className="row" style={{ justifyContent: "flex-end", borderTop: "1px solid var(--line)", paddingTop: 12 }}>
              {viewingCv.saved ? (
                <button
                  type="button"
                  className="btn btn-d btn-sm"
                  onClick={() => void handleUnsave(viewingCv)}
                >
                  Bỏ lưu
                </button>
              ) : (
                <button
                  type="button"
                  className="btn btn-p btn-sm"
                  onClick={() => openSaveDialog(viewingCv)}
                >
                  Lưu CV này
                </button>
              )}
            </div>
          </div>
        </div>
      ) : null}

      {savingTarget ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="save-cv-title"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 60,
            display: "grid",
            placeItems: "center",
            padding: 20,
          }}
        >
          <div className="scrim" onClick={() => setSavingTarget(null)} />
          <form className="modal stack" style={{ gap: 14 }} onSubmit={(e) => void handleConfirmSave(e)}>
            <h2 id="save-cv-title" style={{ fontSize: 20 }}>
              {savingTarget.saved ? `Ghi chú cho ${savingTarget.code}` : `Lưu ${savingTarget.code}`}
            </h2>
            <div className="field">
              <label htmlFor="cv-save-note">Ghi chú nội bộ (không bắt buộc)</label>
              <textarea
                id="cv-save-note"
                className="input"
                placeholder="VD: Phù hợp team Payment, liên hệ khi mở tin Q1."
                value={noteInput}
                onChange={(e) => setNoteInput(e.target.value)}
                style={{ minHeight: 90 }}
              />
            </div>
            <div className="row" style={{ justifyContent: "flex-end" }}>
              <button
                type="button"
                className="btn btn-g btn-sm"
                onClick={() => setSavingTarget(null)}
              >
                Huỷ
              </button>
              <button type="submit" className="btn btn-p btn-sm" disabled={busy}>
                {busy ? "Đang lưu…" : "Lưu"}
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </RecruiterLayout>
  );
}
