import { useCallback, useEffect, useMemo, useState } from "react";
import { MAX_PAGE_SIZE, type JobDto } from "../../api/client";
import {
  JOB_LOCK_REASONS,
  getJobLockStates,
  listAdminJobs,
  lockAdminJob,
  unlockAdminJob,
  type JobLockState,
} from "../../api/mock/adminMock";
import { EmptyNote, RecruiterLayout } from "../../components/common";
import { useToast } from "../../context/ToastContext";
import { jobBadge, shortDate } from "../../utils/format";

type JobTabKey = "ALL" | "PUBLISHED" | "LOCKED" | "EXPIRED";

const JOB_TABS: { key: JobTabKey; label: string }[] = [
  { key: "ALL", label: "Tất cả" },
  { key: "PUBLISHED", label: "Đang đăng" },
  { key: "LOCKED", label: "Bị khoá" },
  { key: "EXPIRED", label: "Hết hạn" },
];

/** Màn AD04 · Quản lý tin tuyển dụng (design canvas AdminJobs.dc.html). */
export function AdminJobsPage() {
  const { toast } = useToast();
  const [jobs, setJobs] = useState<JobDto[] | null>(null);
  const [lockMap, setLockMap] = useState<Record<number, JobLockState>>({});
  const [tab, setTab] = useState<JobTabKey>("ALL");
  const [query, setQuery] = useState("");
  const [companyFilter, setCompanyFilter] = useState("all");
  const [lockingJob, setLockingJob] = useState<JobDto | null>(null);
  const [lockReason, setLockReason] = useState(JOB_LOCK_REASONS[0]);
  const [lockNote, setLockNote] = useState("");
  const [busy, setBusy] = useState(false);

  const refreshLocks = useCallback(async () => {
    const [page, locks] = await Promise.all([listAdminJobs({ size: MAX_PAGE_SIZE }), getJobLockStates()]);
    setJobs(page.content);
    setLockMap(locks);
  }, []);

  useEffect(() => {
    Promise.all([listAdminJobs({ size: MAX_PAGE_SIZE }), getJobLockStates()])
      .then(([page, locks]) => {
        setJobs(page.content);
        setLockMap(locks);
      })
      .catch((e: unknown) => {
        setJobs([]);
        toast(e instanceof Error ? e.message : "Không tải được danh sách tin tuyển dụng.");
      });
  }, [toast]);

  function effectiveStatus(job: JobDto): string {
    if (lockMap[job.id]?.locked) return "LOCKED";
    return (job.status || "PUBLISHED").toUpperCase();
  }

  const companies = useMemo(
    () => [...new Set((jobs ?? []).map((j) => j.company).filter(Boolean))].sort((a, b) => a.localeCompare(b, "vi")),
    [jobs]
  );

  const counts = useMemo(() => {
    const c: Record<JobTabKey, number> = { ALL: 0, PUBLISHED: 0, LOCKED: 0, EXPIRED: 0 };
    for (const j of jobs ?? []) {
      c.ALL += 1;
      const st = lockMap[j.id]?.locked ? "LOCKED" : (j.status || "PUBLISHED").toUpperCase();
      if (st === "PUBLISHED") c.PUBLISHED += 1;
      else if (st === "LOCKED") c.LOCKED += 1;
      else if (st === "EXPIRED") c.EXPIRED += 1;
    }
    return c;
  }, [jobs, lockMap]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return (jobs ?? []).filter((j) => {
      const st = lockMap[j.id]?.locked ? "LOCKED" : (j.status || "PUBLISHED").toUpperCase();
      if (tab !== "ALL" && st !== tab) return false;
      if (companyFilter !== "all" && j.company !== companyFilter) return false;
      if (needle) {
        const hay = `${j.title} ${j.company}`.toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      return true;
    });
  }, [jobs, lockMap, tab, companyFilter, query]);

  function startLock(job: JobDto) {
    setLockingJob(job);
    setLockReason(JOB_LOCK_REASONS[0]);
    setLockNote("");
  }

  async function confirmLock() {
    if (!lockingJob) return;
    setBusy(true);
    try {
      await lockAdminJob(lockingJob.id, lockReason, lockNote, lockingJob.title);
      await refreshLocks();
      toast(`Đã khoá tin “${lockingJob.title}”`);
      setLockingJob(null);
      setLockNote("");
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : "Không khoá được tin.");
    } finally {
      setBusy(false);
    }
  }

  async function onUnlock(job: JobDto) {
    setBusy(true);
    try {
      await unlockAdminJob(job.id, job.title);
      await refreshLocks();
      toast(`Đã mở khoá tin “${job.title}”`);
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : "Không mở khoá được tin.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RecruiterLayout active="adminJobs">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1 style={{ fontSize: 32 }}>Tin tuyển dụng</h1>
          <p className="muted">Xem toàn bộ tin, khoá tin vi phạm. Tin bị khoá bị ẩn khỏi trang công khai.</p>
        </div>
      </div>

      <div className="tabs" role="tablist" aria-label="Lọc tin theo trạng thái">
        {JOB_TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            className={tab === t.key ? "tab tab-on" : "tab"}
            onClick={() => setTab(t.key)}
          >
            {t.label}
            <span className="count">{counts[t.key]}</span>
          </button>
        ))}
      </div>

      <div className="row">
        <input
          className="input"
          type="search"
          placeholder="Tìm tiêu đề, công ty"
          aria-label="Tìm tin"
          style={{ flex: "1 1 260px", maxWidth: 360 }}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          className="input"
          aria-label="Lọc theo công ty"
          style={{ width: "auto" }}
          value={companyFilter}
          onChange={(e) => setCompanyFilter(e.target.value)}
        >
          <option value="all">Mọi công ty</option>
          {companies.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {jobs === null ? (
        <p className="muted">Đang tải danh sách tin tuyển dụng…</p>
      ) : filtered.length === 0 ? (
        <EmptyNote>
          {jobs.length === 0 ? "Hệ thống chưa có tin tuyển dụng nào." : "Không có tin tuyển dụng khớp bộ lọc."}
        </EmptyNote>
      ) : (
        <div className="tbl-box">
          <table className="tbl" style={{ minWidth: 920 }}>
            <thead>
              <tr>
                <th>Tin</th>
                <th>Công ty</th>
                <th>Cấp bậc</th>
                <th>Ngày đăng</th>
                <th>Trạng thái</th>
                <th style={{ textAlign: "right" }}>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((job) => {
                const lockInfo = lockMap[job.id];
                const isLocked = Boolean(lockInfo?.locked);
                const status = effectiveStatus(job);
                const b = jobBadge(status);

                return (
                  <tr key={job.id}>
                    <td>
                      <span style={{ fontWeight: 650 }}>{job.title}</span>
                      {isLocked && lockInfo ? (
                        <p className="tiny" style={{ color: "var(--danger)", marginTop: 4 }}>
                          Lý do khoá: {lockInfo.reason}
                          {lockInfo.note ? ` — ${lockInfo.note}` : ""}
                        </p>
                      ) : null}
                    </td>
                    <td className="small">{job.company}</td>
                    <td className="small">{job.level ?? "—"}</td>
                    <td className="small muted">{job.postedAt ? shortDate(job.postedAt) : "—"}</td>
                    <td>
                      <span className={b.cls}>{b.label}</span>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      {isLocked ? (
                        <button
                          type="button"
                          className="btn btn-g btn-sm"
                          disabled={busy}
                          onClick={() => void onUnlock(job)}
                        >
                          Mở khoá
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="btn btn-d btn-sm"
                          disabled={busy}
                          onClick={() => startLock(job)}
                        >
                          Khoá
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {lockingJob ? (
        <section className="card stack" style={{ gap: 12, maxWidth: 560 }}>
          <h3 style={{ fontSize: 18 }}>Khoá tin: “{lockingJob.title}”</h3>
          <div className="field">
            <label htmlFor="job-lock-reason">Lý do (gửi cho nhà tuyển dụng)</label>
            <select
              id="job-lock-reason"
              className="input"
              value={lockReason}
              onChange={(e) => setLockReason(e.target.value)}
            >
              {JOB_LOCK_REASONS.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="job-lock-note">Ghi chú thêm</label>
            <textarea
              id="job-lock-note"
              className="input"
              placeholder="Ví dụ: Mức lương không thực tế, yêu cầu nộp phí trước."
              style={{ minHeight: 80 }}
              value={lockNote}
              onChange={(e) => setLockNote(e.target.value)}
            />
          </div>
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button
              type="button"
              className="btn btn-g"
              onClick={() => {
                setLockingJob(null);
                setLockNote("");
              }}
            >
              Huỷ
            </button>
            <button
              type="button"
              className="btn btn-d"
              disabled={busy}
              onClick={() => void confirmLock()}
            >
              Khoá tin
            </button>
          </div>
        </section>
      ) : null}
    </RecruiterLayout>
  );
}
