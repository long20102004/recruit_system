import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { EmptyNote, RecruiterLayout } from "../../components/common";
import { MAX_PAGE_SIZE, applicationsApi, getToken, type ApplicationDto } from "../../api/client";
import {
  getApplicationDetailMock,
  saveMockApplicationNote,
  updateMockApplicationStatus,
  type ApplicationDetailMock,
} from "../../api/mock/recruiterMock";
import { useToast } from "../../context/ToastContext";
import { applicationBadge, initials, shortDate } from "../../utils/format";

type DetailTab = "cv" | "cover" | "interview";

interface StatusOption {
  value: string;
  label: string;
}

function nextStatusOptions(currentStatus: string): StatusOption[] {
  switch (currentStatus.toUpperCase()) {
    case "SUBMITTED":
      return [
        { value: "REVIEWING", label: "Đang xem xét (REVIEWING)" },
        { value: "INTERVIEW", label: "Mời phỏng vấn (INTERVIEW)" },
        { value: "REJECTED", label: "Từ chối (REJECTED)" },
      ];
    case "REVIEWING":
      return [
        { value: "INTERVIEW", label: "Mời phỏng vấn (INTERVIEW)" },
        { value: "HIRED", label: "Trúng tuyển (HIRED)" },
        { value: "REJECTED", label: "Từ chối (REJECTED)" },
      ];
    case "INTERVIEW":
      return [
        { value: "HIRED", label: "Trúng tuyển (HIRED)" },
        { value: "REJECTED", label: "Từ chối (REJECTED)" },
      ];
    default:
      return [
        { value: "REVIEWING", label: "Đang xem xét (REVIEWING)" },
        { value: "INTERVIEW", label: "Mời phỏng vấn (INTERVIEW)" },
        { value: "HIRED", label: "Trúng tuyển (HIRED)" },
        { value: "REJECTED", label: "Từ chối (REJECTED)" },
      ];
  }
}

export function RecruiterApplicationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { toast } = useToast();

  const [loading, setLoading] = useState(true);
  const [app, setApp] = useState<ApplicationDto | null>(null);
  const [detail, setDetail] = useState<ApplicationDetailMock | null>(null);
  const [tab, setTab] = useState<DetailTab>("cv");

  const [nextStatus, setNextStatus] = useState("HIRED");
  const [statusNote, setStatusNote] = useState("");
  const [rating, setRating] = useState(4);
  const [internalNote, setInternalNote] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const numericId = Number(id);

    async function load() {
      setLoading(true);
      if (!Number.isFinite(numericId) || numericId <= 0) {
        if (!cancelled) {
          setApp(null);
          setDetail(null);
          setLoading(false);
        }
        return;
      }

      try {
        const page = await applicationsApi.recruiter({ size: MAX_PAGE_SIZE });
        const found = page.content.find((item) => item.id === numericId) ?? null;
        if (!found) {
          if (!cancelled) {
            setApp(null);
            setDetail(null);
          }
          return;
        }
        const mockData = await getApplicationDetailMock({
          id: found.id,
          candidateName: found.candidateName,
          jobTitle: found.jobTitle,
          status: found.status,
          appliedAt: found.appliedAt,
        });
        if (!cancelled) {
          setApp(found);
          setDetail(mockData);
          setRating(mockData.rating);
          setInternalNote(mockData.internalNote);
          const effective = mockData.overrideStatus ?? found.status;
          const opts = nextStatusOptions(effective);
          setNextStatus(opts[0]?.value ?? "HIRED");
        }
      } catch (e) {
        if (!cancelled) {
          setApp(null);
          setDetail(null);
          toast(e instanceof Error ? e.message : "Không tải được chi tiết đơn ứng tuyển");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [id, toast]);

  const effectiveStatus = detail?.overrideStatus ?? app?.status ?? "SUBMITTED";
  const statusOptions = useMemo(() => nextStatusOptions(effectiveStatus), [effectiveStatus]);
  const badge = applicationBadge(effectiveStatus);

  async function applyStatusChange(targetStatus: string, note: string) {
    if (!app) return;
    setBusy(true);
    try {
      const updated = await updateMockApplicationStatus(app.id, targetStatus, note);
      setDetail(updated);
      setStatusNote("");
      const nextOpts = nextStatusOptions(targetStatus);
      setNextStatus(nextOpts[0]?.value ?? targetStatus);
      const nextBadge = applicationBadge(targetStatus);
      toast(`Đã cập nhật trạng thái đơn sang "${nextBadge.label}".`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Cập nhật trạng thái thất bại");
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveInternalNote() {
    if (!app) return;
    setBusy(true);
    try {
      const updated = await saveMockApplicationNote(app.id, rating, internalNote);
      setDetail(updated);
      toast("Đã lưu ghi chú nội bộ và đánh giá.");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Lưu ghi chú thất bại");
    } finally {
      setBusy(false);
    }
  }

  async function handleDownloadCv() {
    if (!app) return;
    if (detail?.hasCvFile === false) {
      toast("Ứng viên chưa tải lên tệp CV PDF gốc.");
      return;
    }
    try {
      const token = getToken();
      const res = await fetch(applicationsApi.cvFileUrl(app.id), {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!res.ok) {
        toast("Không có tệp CV để tải xuống.");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = detail?.cvFileName || `cv-ung-vien-${app.id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch {
      toast("Không tải được tệp CV.");
    }
  }

  return (
    <RecruiterLayout active="candidates">
      {loading ? (
        <p className="muted">Đang tải chi tiết đơn ứng tuyển…</p>
      ) : !app || !detail ? (
        <EmptyNote>
          <p>Không tìm thấy đơn ứng tuyển.</p>
          <Link to="/recruiter/candidates" className="btn btn-g btn-sm" style={{ marginTop: 12 }}>
            Quay lại danh sách đơn
          </Link>
        </EmptyNote>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <nav className="small muted row" style={{ gap: 6 }} aria-label="Breadcrumb">
            <Link to="/recruiter/candidates">Đơn ứng tuyển</Link>
            <span>/</span>
            <span>{app.jobTitle}</span>
            <span>/</span>
            <span style={{ color: "var(--ink)" }}>{app.candidateName}</span>
          </nav>

          <section
            className="card"
            style={{
              padding: 24,
              display: "flex",
              gap: 20,
              flexWrap: "wrap",
              alignItems: "center",
            }}
          >
            <span className="avatar" style={{ width: 64, height: 64, fontSize: 20 }}>
              {initials(app.candidateName)}
            </span>
            <div style={{ flex: "1 1 320px", display: "flex", flexDirection: "column", gap: 4 }}>
              <div className="row" style={{ gap: 10 }}>
                <h1 style={{ fontSize: 28 }}>{app.candidateName}</h1>
                <span className={badge.cls}>{badge.label}</span>
              </div>
              <p className="small muted">
                {detail.cv.roleTitle} · {detail.cv.yearsExpLabel} · {detail.cv.email} · {detail.cv.phone}
              </p>
              <p className="small muted">
                Nộp {shortDate(app.appliedAt)} cho{" "}
                <strong style={{ color: "var(--ink)" }}>{app.jobTitle}</strong>
              </p>
            </div>
            <div className="row" style={{ gap: 8 }}>
              <button
                type="button"
                className="btn btn-g"
                onClick={() => void handleDownloadCv()}
              >
                Tải CV
              </button>
              <button
                type="button"
                className="btn btn-d"
                disabled={busy}
                onClick={() => void applyStatusChange("REJECTED", statusNote)}
              >
                Từ chối
              </button>
              <button
                type="button"
                className="btn btn-ok"
                disabled={busy}
                onClick={() => void applyStatusChange("HIRED", statusNote)}
              >
                Nhận (Trúng tuyển)
              </button>
            </div>
          </section>

          <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>
            <div style={{ flex: "999 1 520px", minWidth: 0, display: "flex", flexDirection: "column", gap: 18 }}>
              <div className="tabs" role="tablist" aria-label="Nội dung hồ sơ">
                <button
                  type="button"
                  role="tab"
                  aria-selected={tab === "cv"}
                  className={tab === "cv" ? "tab tab-on" : "tab"}
                  onClick={() => setTab("cv")}
                >
                  CV
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={tab === "cover"}
                  className={tab === "cover" ? "tab tab-on" : "tab"}
                  onClick={() => setTab("cover")}
                >
                  Thư giới thiệu
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={tab === "interview"}
                  className={tab === "interview" ? "tab tab-on" : "tab"}
                  onClick={() => setTab("interview")}
                >
                  Kết quả phỏng vấn
                </button>
              </div>

              {tab === "cv" ? (
                <section className="card stack" style={{ gap: 18, padding: 26 }}>
                  <div>
                    <p className="kicker" style={{ color: "var(--muted)" }}>
                      Giới thiệu
                    </p>
                    <p style={{ marginTop: 6, color: "var(--ink-soft)" }}>{detail.cv.summary}</p>
                  </div>

                  <div>
                    <p className="kicker" style={{ color: "var(--muted)" }}>
                      Kinh nghiệm
                    </p>
                    <div style={{ marginTop: 8, display: "grid", gap: 12 }}>
                      {detail.cv.experiences.map((exp) => (
                        <div key={`${exp.title}-${exp.period}`}>
                          <div className="between">
                            <p style={{ fontWeight: 650 }}>{exp.title}</p>
                            <span className="small muted">{exp.period}</span>
                          </div>
                          <p className="small" style={{ color: "var(--ink-soft)" }}>
                            {exp.description}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <p className="kicker" style={{ color: "var(--muted)" }}>
                      Học vấn
                    </p>
                    <p style={{ marginTop: 6 }}>{detail.cv.education}</p>
                  </div>

                  <div>
                    <p className="kicker" style={{ color: "var(--muted)" }}>
                      Kỹ năng
                    </p>
                    <div className="row" style={{ gap: 6, marginTop: 8 }}>
                      {detail.cv.matchedSkills.map((s) => (
                        <span key={s} className="tag tag-on">
                          {s}
                        </span>
                      ))}
                      {detail.cv.otherSkills.map((s) => (
                        <span key={s} className="tag">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                </section>
              ) : tab === "cover" ? (
                <section className="card stack" style={{ gap: 12, padding: 26 }}>
                  <h3 style={{ fontSize: 18 }}>Thư giới thiệu</h3>
                  {app.coverLetter?.trim() ? (
                    <p style={{ color: "var(--ink-soft)", whiteSpace: "pre-line" }}>
                      {app.coverLetter}
                    </p>
                  ) : (
                    <EmptyNote>Ứng viên không đính kèm thư giới thiệu khi nộp đơn.</EmptyNote>
                  )}
                </section>
              ) : (
                <section className="card stack" style={{ gap: 12, padding: 26 }}>
                  <div className="between">
                    <h3 style={{ fontSize: 18 }}>Kết quả phỏng vấn</h3>
                    <Link
                      to="/recruiter/interview-results"
                      className="small"
                      style={{ color: "var(--brand)", fontWeight: 650 }}
                    >
                      Danh sách kết quả phỏng vấn
                    </Link>
                  </div>
                  {detail.interview ? (
                    <>
                      <div className="row" style={{ gap: 24 }}>
                        <p className="disp" style={{ fontSize: 40, color: "var(--brand)" }}>
                          {detail.interview.overallScore.toFixed(1).replace(".", ",")}
                          <span className="small muted" style={{ fontFamily: "var(--font-body)" }}>
                            /10
                          </span>
                        </p>
                        <p className="small muted">
                          Hoàn thành {detail.interview.completedAt} · {detail.interview.questionCount} câu ·{" "}
                          {detail.interview.durationMinutes} phút
                        </p>
                      </div>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 180px), 1fr))",
                          gap: 12,
                        }}
                      >
                        {detail.interview.topics.map((t) => (
                          <div key={t.name}>
                            <div className="between tiny" style={{ marginBottom: 4 }}>
                              <span className="muted">{t.name}</span>
                              <strong>{t.score.toFixed(1).replace(".", ",")}</strong>
                            </div>
                            <div className="meter">
                              <span style={{ width: `${Math.min(100, t.score * 10)}%` }} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <EmptyNote>Ứng viên chưa hoàn thành phiên phỏng vấn nào cho đơn này.</EmptyNote>
                  )}
                </section>
              )}
            </div>

            <aside style={{ flex: "1 1 320px", maxWidth: 380, display: "flex", flexDirection: "column", gap: 16 }}>
              <section className="card stack" style={{ gap: 10 }}>
                <h4>Điểm phù hợp</h4>
                <p className="disp" style={{ fontSize: 40, color: "var(--brand)" }}>
                  {detail.match.overallPercent}%
                </p>
                {detail.match.breakdown.map((m) => (
                  <div
                    key={m.label}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "100px 1fr 40px",
                      gap: 10,
                      alignItems: "center",
                      fontSize: 13,
                    }}
                  >
                    <span>{m.label}</span>
                    <div className="meter">
                      <span style={{ width: `${m.percent}%` }} />
                    </div>
                    <strong style={{ textAlign: "right" }}>{m.percent}%</strong>
                  </div>
                ))}
                {detail.match.missingSkills.length > 0 ? (
                  <p className="small">
                    Thiếu:{" "}
                    <strong style={{ color: "var(--warn)" }}>
                      {detail.match.missingSkills.join(", ")}
                    </strong>
                  </p>
                ) : null}
              </section>

              <section className="card stack" style={{ gap: 10 }}>
                <h4>Chuyển trạng thái</h4>
                <select
                  className="input"
                  aria-label="Trạng thái mới"
                  value={nextStatus}
                  onChange={(e) => setNextStatus(e.target.value)}
                >
                  {statusOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <textarea
                  className="input"
                  placeholder="Ghi chú gửi kèm (không bắt buộc)"
                  aria-label="Ghi chú chuyển trạng thái"
                  value={statusNote}
                  onChange={(e) => setStatusNote(e.target.value)}
                  style={{ minHeight: 80 }}
                />
                <button
                  type="button"
                  className="btn btn-p"
                  disabled={busy}
                  onClick={() => void applyStatusChange(nextStatus, statusNote)}
                >
                  Cập nhật trạng thái
                </button>
                <p className="help">
                  {effectiveStatus.toUpperCase() === "INTERVIEW"
                    ? "Đơn ở Phỏng vấn chỉ chuyển được sang Trúng tuyển hoặc Từ chối."
                    : "Thao tác cập nhật trạng thái sẽ được ghi nhận vào lịch sử xử lý đơn."}
                </p>
              </section>

              <section className="card stack" style={{ gap: 10 }}>
                <h4>Ghi chú nội bộ &amp; đánh giá</h4>
                <div className="row" style={{ gap: 4 }} role="group" aria-label={`Đánh giá ${rating} trên 5 sao`}>
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      aria-label={`${star} sao`}
                      onClick={() => setRating(star)}
                      style={{
                        all: "unset",
                        cursor: "pointer",
                        fontSize: 22,
                        lineHeight: 1,
                        color: star <= rating ? "var(--gold)" : "var(--line-strong)",
                      }}
                    >
                      ★
                    </button>
                  ))}
                </div>
                <textarea
                  className="input"
                  aria-label="Ghi chú nội bộ"
                  value={internalNote}
                  onChange={(e) => setInternalNote(e.target.value)}
                  style={{ minHeight: 80 }}
                />
                <div className="between">
                  <span className="tiny muted">Chỉ thành viên công ty thấy.</span>
                  <button
                    type="button"
                    className="btn btn-g btn-sm"
                    disabled={busy}
                    onClick={() => void handleSaveInternalNote()}
                  >
                    Lưu ghi chú
                  </button>
                </div>
              </section>

              <section className="card stack" style={{ gap: 2 }}>
                <h4 style={{ marginBottom: 8 }}>Lịch sử</h4>
                {detail.history.map((h, idx) => (
                  <div
                    key={`${h.statusLabel}-${h.timestamp}-${idx}`}
                    style={{ padding: "8px 0", borderTop: "1px solid var(--line)" }}
                  >
                    <p className="small" style={{ fontWeight: 600 }}>
                      {h.statusLabel}
                    </p>
                    <p className="tiny muted">
                      {h.timestamp} · {h.actor}
                    </p>
                    {h.note ? (
                      <p className="tiny" style={{ color: "var(--ink-soft)", marginTop: 2 }}>
                        “{h.note}”
                      </p>
                    ) : null}
                  </div>
                ))}
              </section>
            </aside>
          </div>
        </div>
      )}
    </RecruiterLayout>
  );
}
