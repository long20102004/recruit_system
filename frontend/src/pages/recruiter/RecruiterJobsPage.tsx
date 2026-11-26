import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Button,
  Can,
  EmptyNote,
  PageHead,
  RecruiterLayout,
  Table,
} from "../../components/common";
import { MAX_PAGE_SIZE, applicationsApi, jobsApi, type JobDto } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { jobBadge, shortDate } from "../../utils/format";
import { mapJob } from "../../utils/mappers";

type JobStatusTab = "ALL" | "PUBLISHED" | "DRAFT" | "CLOSED";

const STATUS_TABS: ReadonlyArray<{ key: JobStatusTab; label: string }> = [
  { key: "ALL", label: "Tất cả" },
  { key: "PUBLISHED", label: "Đang đăng" },
  { key: "DRAFT", label: "Nháp" },
  { key: "CLOSED", label: "Đã đóng" },
];

export function RecruiterJobsPage() {
  const { toast } = useToast();
  const [jobs, setJobs] = useState<JobDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<JobStatusTab>("ALL");
  const [keyword, setKeyword] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [appCount, setAppCount] = useState<Map<number, number> | null>(null);
  const { can } = useAuth();
  const canReadApps = can("application:read-received");

  const load = useCallback(async () => {
    const page = await jobsApi.mine({ size: MAX_PAGE_SIZE });
    setJobs(page.content);
    if (canReadApps) {
      const apps = await applicationsApi.recruiter({ size: MAX_PAGE_SIZE });
      const counts = new Map<number, number>();
      for (const a of apps.content) counts.set(a.jobId, (counts.get(a.jobId) ?? 0) + 1);
      setAppCount(counts);
    }
  }, [canReadApps]);

  useEffect(() => {
    load()
      .catch((e) =>
        toast(e instanceof Error ? e.message : "Không tải được danh sách tin")
      )
      .finally(() => setLoading(false));
  }, [load, toast]);

  const counts = useMemo(() => {
    const map: Record<JobStatusTab, number> = {
      ALL: jobs.length,
      PUBLISHED: 0,
      DRAFT: 0,
      CLOSED: 0,
    };
    for (const j of jobs) {
      const s = (j.status ?? "").toUpperCase();
      if (s === "PUBLISHED" || s === "DRAFT" || s === "CLOSED") {
        map[s] += 1;
      }
    }
    return map;
  }, [jobs]);

  const filtered = useMemo(() => {
    const q = keyword.trim().toLowerCase();
    return jobs.filter((j) => {
      if (tab !== "ALL" && (j.status ?? "").toUpperCase() !== tab) {
        return false;
      }
      if (q && !j.title.toLowerCase().includes(q)) {
        return false;
      }
      return true;
    });
  }, [jobs, tab, keyword]);

  async function handleStatusChange(
    jobId: number,
    nextStatus: "CLOSED" | "PUBLISHED"
  ) {
    setBusyId(jobId);
    try {
      await jobsApi.updateStatus(jobId, nextStatus);
      toast(
        nextStatus === "CLOSED"
          ? "Đã đóng tin tuyển dụng"
          : "Đã mở lại tin tuyển dụng"
      );
      await load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Cập nhật trạng thái thất bại");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <RecruiterLayout active="jobs">
      <PageHead
        title="Tin tuyển dụng"
        description="Đăng, đóng và mở lại tin tuyển dụng của công ty."
        actions={
          <Can perm="job:create">
            <Button variant="primary" to="/recruiter/jobs/new">
              + Đăng tin mới
            </Button>
          </Can>
        }
      />

      <div className="tabs" role="tablist" aria-label="Lọc theo trạng thái tin">
        {STATUS_TABS.map((t) => {
          const active = tab === t.key;
          return (
            <button
              key={t.key}
              type="button"
              role="tab"
              aria-selected={active}
              className={active ? "tab tab-on" : "tab"}
              onClick={() => setTab(t.key)}
            >
              {t.label}
              <span className="count">{counts[t.key]}</span>
            </button>
          );
        })}
      </div>

      <div className="row">
        <div className="field" style={{ flex: "1 1 280px", maxWidth: 380 }}>
          <input
            className="input"
            type="search"
            placeholder="Tìm theo tiêu đề tin"
            aria-label="Tìm theo tiêu đề tin"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <EmptyNote>Đang tải danh sách tin tuyển dụng…</EmptyNote>
      ) : filtered.length === 0 ? (
        <EmptyNote>
          {jobs.length === 0
            ? "Chưa có tin tuyển dụng nào. Nhấn “+ Đăng tin mới” để bắt đầu."
            : "Không có tin nào khớp bộ lọc hiện tại."}
        </EmptyNote>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Tin</th>
              {appCount ? <th>Ứng viên</th> : null}
              <th>Ngày đăng</th>
              <th>Trạng thái</th>
              <th style={{ textAlign: "right" }}>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((j) => {
              const badge = jobBadge(j.status);
              const mapped = mapJob(j);
              const status = (j.status ?? "").toUpperCase();
              const isBusy = busyId === j.id;
              return (
                <tr key={j.id}>
                  <td>
                    <p style={{ fontWeight: 650 }}>{j.title}</p>
                    <p className="tiny muted">
                      {[mapped.location, mapped.salary].filter(Boolean).join(" · ")}
                    </p>
                  </td>
                  {appCount ? <td>{appCount.get(j.id) ?? 0}</td> : null}
                  <td className="small muted">{shortDate(j.postedAt) || "—"}</td>
                  <td>
                    <span className={badge.cls}>{badge.label}</span>
                  </td>
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    <Can perm="job:update">
                      {status === "PUBLISHED" ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={isBusy}
                          onClick={() => void handleStatusChange(j.id, "CLOSED")}
                        >
                          {isBusy ? "Đang xử lý…" : "Đóng tin"}
                        </Button>
                      ) : status === "CLOSED" ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={isBusy}
                          onClick={() =>
                            void handleStatusChange(j.id, "PUBLISHED")
                          }
                        >
                          {isBusy ? "Đang xử lý…" : "Mở lại"}
                        </Button>
                      ) : null}
                    </Can>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      )}
    </RecruiterLayout>
  );
}
