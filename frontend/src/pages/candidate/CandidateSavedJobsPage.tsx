import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyNote, JobLogo, MockNote, SiteHeader } from "../../components/common";
import { savedJobsMock, type SavedJobItem } from "../../api/mock/candidateMock";
import { useToast } from "../../context/ToastContext";

/** Màn C07 · Việc đã lưu (design canvas SavedJobs.dc.html). */

type SavedTab = "OPEN" | "CLOSED";

export function CandidateSavedJobsPage() {
  const { toast } = useToast();
  const [jobs, setJobs] = useState<SavedJobItem[] | null>(null);
  const [tab, setTab] = useState<SavedTab>("OPEN");
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    savedJobsMock
      .list()
      .then(setJobs)
      .catch((e) => {
        setJobs([]);
        toast(e instanceof Error ? e.message : "Không tải được danh sách việc đã lưu");
      });
  }, [toast]);

  const openJobs = useMemo(
    () => (jobs ?? []).filter((j) => j.status === "OPEN"),
    [jobs]
  );

  const closedJobs = useMemo(
    () => (jobs ?? []).filter((j) => j.status !== "OPEN"),
    [jobs]
  );

  const shown = tab === "OPEN" ? openJobs : closedJobs;

  async function onUnsave(item: SavedJobItem) {
    setBusyId(item.id);
    try {
      await savedJobsMock.unsave(item.id);
      setJobs((prev) => (prev ? prev.filter((j) => j.id !== item.id) : prev));
      toast(`Đã bỏ lưu “${item.title}”.`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không thể bỏ lưu việc làm");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <SiteHeader active="applications" mode="candidate" />
      <div
        className="wrap"
        style={{
          paddingTop: 32,
          paddingBottom: 64,
          display: "flex",
          flexDirection: "column",
          gap: 18,
          maxWidth: 980,
        }}
      >
        <MockNote />

        <div className="page-head" style={{ marginBottom: 0 }}>
          <div>
            <h1 style={{ fontSize: 34 }}>Việc đã lưu</h1>
            <p className="muted">
              {jobs?.length ?? 0} việc · Tin đã đóng hoặc hết hạn vẫn hiển thị để bạn tham khảo.
            </p>
          </div>
          <div className="tabs" role="tablist" aria-label="Lọc việc đã lưu" style={{ border: 0 }}>
            <button
              type="button"
              role="tab"
              aria-selected={tab === "OPEN"}
              className={tab === "OPEN" ? "tab tab-on" : "tab"}
              onClick={() => setTab("OPEN")}
            >
              Đang mở
              <span className="count">{openJobs.length}</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === "CLOSED"}
              className={tab === "CLOSED" ? "tab tab-on" : "tab"}
              onClick={() => setTab("CLOSED")}
            >
              Đã đóng / hết hạn
              <span className="count">{closedJobs.length}</span>
            </button>
          </div>
        </div>

        {jobs === null ? (
          <p className="muted">Đang tải…</p>
        ) : shown.length === 0 ? (
          <EmptyNote>
            <p style={{ fontWeight: 650 }}>
              {tab === "OPEN"
                ? "Chưa có tin đang mở nào được lưu."
                : "Không có tin đã đóng hoặc hết hạn."}
            </p>
            {tab === "OPEN" ? (
              <Link to="/candidate" className="btn btn-g btn-sm" style={{ marginTop: 12 }}>
                Tìm việc làm
              </Link>
            ) : null}
          </EmptyNote>
        ) : tab === "OPEN" ? (
          <div className="stack">
            {shown.map((j) => {
              const hasRealId = typeof j.jobId === "number" && j.jobId > 0;
              return (
                <article
                  key={j.id}
                  className="jobcard"
                  style={{ cursor: "default" }}
                >
                  <JobLogo initials={j.logo} />
                  <div
                    style={{
                      flex: "1 1 320px",
                      minWidth: 0,
                      display: "flex",
                      flexDirection: "column",
                      gap: 6,
                    }}
                  >
                    <div className="row" style={{ gap: 8 }}>
                      {j.hot ? <span className="badge b-hot">HOT</span> : null}
                      <span className="tiny muted">
                        Lưu {j.savedAt} · Hạn {j.deadline}
                      </span>
                    </div>
                    <h3 className="jobcard-title">
                      {hasRealId ? (
                        <Link
                          to={`/candidate/jobs/${j.jobId}`}
                          style={{ color: "var(--ink)" }}
                        >
                          {j.title}
                        </Link>
                      ) : (
                        j.title
                      )}
                    </h3>
                    <div className="row small muted" style={{ gap: "6px 14px" }}>
                      <span style={{ fontWeight: 600, color: "var(--ink-soft)" }}>
                        {j.company}
                      </span>
                      <span>{j.city}</span>
                      <span>{j.mode}</span>
                      <span>{j.level}</span>
                    </div>
                    <div className="row" style={{ gap: 6, marginTop: 2 }}>
                      {j.skills.map((s) => (
                        <span key={s} className="tag">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="jobcard-side">
                    <span className="salary-hl">{j.salary}</span>
                    {j.match != null ? (
                      <span className="match">{j.match}% phù hợp</span>
                    ) : null}
                    <div className="row" style={{ gap: 8 }}>
                      {hasRealId ? (
                        <Link to={`/candidate/jobs/${j.jobId}`} className="btn btn-p btn-sm">
                          Xem tin
                        </Link>
                      ) : null}
                      <button
                        type="button"
                        className="btn btn-g btn-sm"
                        disabled={busyId === j.id}
                        onClick={() => onUnsave(j)}
                      >
                        {busyId === j.id ? "Đang xử lý…" : "Bỏ lưu"}
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="stack">
            {shown.map((j) => (
              <article
                key={j.id}
                className="card"
                style={{
                  display: "flex",
                  gap: 16,
                  alignItems: "center",
                  flexWrap: "wrap",
                  opacity: 0.75,
                }}
              >
                <span className="logo">{j.logo}</span>
                <div style={{ flex: "1 1 300px", minWidth: 0 }}>
                  <span className="badge b-plain">
                    {j.status === "CLOSED" ? `Đã đóng ${j.deadline}` : `Hết hạn ${j.deadline}`}
                  </span>
                  <p className="disp" style={{ fontSize: 18, marginTop: 6 }}>
                    {j.title}
                  </p>
                  <p className="small muted">
                    {j.company} · {j.city} · Lưu {j.savedAt}
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn-g btn-sm"
                  disabled={busyId === j.id}
                  onClick={() => onUnsave(j)}
                >
                  {busyId === j.id ? "Đang xử lý…" : "Bỏ lưu"}
                </button>
              </article>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
