import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Button,
  EmptyNote,
  Pager,
  PageHead,
  Panel,
  RecruiterLayout,
  SplitActions,
  Table,
  TextSelect,
} from "../../components/common";
import {
  applicationsApi,
  type ApplicationDto,
  type PageDto,
} from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { applicationBadge, initials, shortDate } from "../../utils/format";

type StatusTab =
  | "ALL"
  | "SUBMITTED"
  | "REVIEWING"
  | "INTERVIEW"
  | "HIRED"
  | "REJECTED"
  | "WITHDRAWN";

const STATUS_TABS: ReadonlyArray<{ key: StatusTab; label: string }> = [
  { key: "ALL", label: "Tất cả" },
  { key: "SUBMITTED", label: "Đã nộp" },
  { key: "REVIEWING", label: "Đang xem xét" },
  { key: "INTERVIEW", label: "Phỏng vấn" },
  { key: "HIRED", label: "Trúng tuyển" },
  { key: "REJECTED", label: "Từ chối" },
  { key: "WITHDRAWN", label: "Đã rút" },
];

type SortOption = "newest" | "oldest" | "name" | "ranking";

export function RecruiterCandidatesPage() {
  const { toast } = useToast();
  const [page, setPage] = useState(0);
  const [data, setData] = useState<PageDto<ApplicationDto> | null>(null);
  const apps = useMemo(() => data?.content ?? [], [data]);

  const [jobFilter, setJobFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusTab>("ALL");
  const [sortBy, setSortBy] = useState<SortOption>("newest");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkStatus, setBulkStatus] = useState<"REVIEWING" | "INTERVIEW" | "HIRED" | "REJECTED">("REVIEWING");
  const [bulkBusy, setBulkBusy] = useState(false);

  const load = useCallback(() => {
    applicationsApi
      .recruiter({ page, rank: sortBy === "ranking" })
      .then((res) => {
        setData(res);
        setSelectedIds(new Set());
      })
      .catch((e) => toast(e.message));
  }, [toast, page, sortBy]);

  useEffect(() => {
    load();
  }, [load]);

  function toggleSelect(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleBulkUpdate() {
    if (selectedIds.size === 0) return;
    setBulkBusy(true);
    try {
      await applicationsApi.bulkUpdateStatus([...selectedIds], bulkStatus);
      toast(`Đã cập nhật ${selectedIds.size} đơn sang trạng thái ${applicationBadge(bulkStatus).label}.`);
      load();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Cập nhật hàng loạt thất bại");
    } finally {
      setBulkBusy(false);
    }
  }

  const jobOptions = useMemo(() => {
    const counts = new Map<string, number>();
    for (const a of apps) {
      if (!a.jobTitle) continue;
      counts.set(a.jobTitle, (counts.get(a.jobTitle) ?? 0) + 1);
    }
    return [...counts.entries()];
  }, [apps]);

  const activeJobFilter = useMemo(() => {
    if (!jobFilter) return "";
    return jobOptions.some(([title]) => title === jobFilter) ? jobFilter : "";
  }, [jobFilter, jobOptions]);

  const statusCounts = useMemo(() => {
    const scoped = activeJobFilter
      ? apps.filter((a) => a.jobTitle === activeJobFilter)
      : apps;
    const map: Record<StatusTab, number> = {
      ALL: scoped.length,
      SUBMITTED: 0,
      REVIEWING: 0,
      INTERVIEW: 0,
      HIRED: 0,
      REJECTED: 0,
      WITHDRAWN: 0,
    };
    for (const a of scoped) {
      const s = (a.status ?? "").toUpperCase();
      if (
        s === "SUBMITTED" ||
        s === "REVIEWING" ||
        s === "INTERVIEW" ||
        s === "HIRED" ||
        s === "REJECTED" ||
        s === "WITHDRAWN"
      ) {
        map[s] += 1;
      }
    }
    return map;
  }, [apps, activeJobFilter]);

  const filtered = useMemo(() => {
    const list = apps.filter((a) => {
      if (activeJobFilter && a.jobTitle !== activeJobFilter) return false;
      if (
        statusFilter !== "ALL" &&
        (a.status ?? "").toUpperCase() !== statusFilter
      ) {
        return false;
      }
      return true;
    });

    if (sortBy === "ranking") return list;
    return [...list].sort((a, b) => {
      if (sortBy === "name") {
        return a.candidateName.localeCompare(b.candidateName, "vi");
      }
      const ta = new Date(a.appliedAt).getTime() || 0;
      const tb = new Date(b.appliedAt).getTime() || 0;
      return sortBy === "oldest" ? ta - tb : tb - ta;
    });
  }, [apps, activeJobFilter, statusFilter, sortBy]);

  return (
    <RecruiterLayout active="candidates">
      <PageHead
        title="Đơn ứng tuyển"
        description="Danh sách đơn ứng tuyển vào các tin bạn đang quản lý."
        actions={
          <label className="field" style={{ minWidth: 320 }}>
            <span className="lbl">Tin tuyển dụng</span>
            <TextSelect
              aria-label="Lọc theo tin tuyển dụng"
              value={activeJobFilter}
              onChange={(e) => setJobFilter(e.target.value)}
            >
              <option value="">Tất cả tin</option>
              {jobOptions.map(([title, count]) => (
                <option key={title} value={title}>
                  {title} ({count} đơn)
                </option>
              ))}
            </TextSelect>
          </label>
        }
      />

      <div className="tabs" role="tablist" aria-label="Lọc theo trạng thái đơn">
        {STATUS_TABS.map((t) => {
          const active = statusFilter === t.key;
          return (
            <button
              key={t.key}
              type="button"
              role="tab"
              aria-selected={active}
              className={active ? "tab tab-on" : "tab"}
              onClick={() => setStatusFilter(t.key)}
            >
              {t.label}
              <span className="count">{statusCounts[t.key]}</span>
            </button>
          );
        })}
      </div>

      <div className="row">
        <TextSelect
          aria-label="Sắp xếp"
          value={sortBy}
          onChange={(e) => { setSortBy(e.target.value as SortOption); setPage(0); }}
          style={{ width: "auto" }}
        >
          <option value="newest">Mới nộp nhất</option>
          <option value="oldest">Nộp sớm nhất</option>
          <option value="name">Tên ứng viên A–Z</option>
          <option value="ranking">Điểm tổng hợp</option>
        </TextSelect>
        <Button
          variant="ghost"
          to="/recruiter/matching"
          style={{ marginLeft: "auto" }}
        >
          Chạy lại matching
        </Button>
      </div>

      {selectedIds.size > 0 ? (
        <div className="card row" style={{ gap: 12, padding: "12px 16px", alignItems: "center" }}>
          <strong className="small">Đã chọn {selectedIds.size} đơn</strong>
          <TextSelect
            aria-label="Trạng thái hàng loạt"
            value={bulkStatus}
            onChange={(e) => setBulkStatus(e.target.value as "REVIEWING" | "INTERVIEW" | "HIRED" | "REJECTED")}
            style={{ width: "auto" }}
          >
            <option value="REVIEWING">Đang xem xét</option>
            <option value="INTERVIEW">Mời phỏng vấn</option>
            <option value="HIRED">Trúng tuyển</option>
            <option value="REJECTED">Từ chối</option>
          </TextSelect>
          <Button variant="primary" size="sm" disabled={bulkBusy} onClick={() => void handleBulkUpdate()}>
            {bulkBusy ? "Đang cập nhật…" : "Cập nhật hàng loạt"}
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setSelectedIds(new Set())}>
            Bỏ chọn
          </Button>
        </div>
      ) : null}

      <Panel>
        {filtered.length === 0 ? (
          <EmptyNote>
            {apps.length === 0
              ? "Chưa có ứng viên nộp hồ sơ."
              : "Không có đơn nào khớp bộ lọc trên trang này."}
          </EmptyNote>
        ) : (
          <Table>
            <thead>
              <tr>
                <th style={{ width: 32 }}>
                  <input
                    type="checkbox"
                    aria-label="Chọn tất cả đơn đang hiển thị"
                    checked={filtered.length > 0 && filtered.every((a) => selectedIds.has(a.id))}
                    onChange={(e) =>
                      setSelectedIds(e.target.checked ? new Set(filtered.map((a) => a.id)) : new Set())
                    }
                  />
                </th>
                <th>Ứng viên</th>
                <th>Vị trí</th>
                <th>Công ty</th>
                <th>Trạng thái</th>
                <th>Ngày nộp</th>
                {sortBy === "ranking" && <th>Điểm tổng hợp</th>}
                <th style={{ textAlign: "right" }}>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((a) => {
                const b = applicationBadge(a.status);
                return (
                  <tr key={a.id}>
                    <td>
                      <input
                        type="checkbox"
                        aria-label={`Chọn đơn của ${a.candidateName}`}
                        checked={selectedIds.has(a.id)}
                        onChange={() => toggleSelect(a.id)}
                      />
                    </td>
                    <td>
                      <div
                        className="row"
                        style={{ gap: 10, flexWrap: "nowrap" }}
                      >
                        <span className="avatar">
                          {initials(a.candidateName)}
                        </span>
                        <Link
                          to={`/recruiter/candidates/${a.id}`}
                          style={{ fontWeight: 650 }}
                        >
                          {a.candidateName}
                        </Link>
                      </div>
                    </td>
                    <td className="small">{a.jobTitle}</td>
                    <td className="small">{a.companyName}</td>
                    <td>
                      <span className={b.cls}>{b.label}</span>
                    </td>
                    <td className="small muted">{shortDate(a.appliedAt)}</td>
                    {sortBy === "ranking" && (
                      <td>{a.rankingScore == null ? "—" : `${Math.round(a.rankingScore * 100)}%`}</td>
                    )}
                    <td style={{ textAlign: "right" }}>
                      <Link
                        to={`/recruiter/candidates/${a.id}`}
                        className="btn btn-g btn-sm"
                      >
                        Xem
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
        <Pager data={data} onPage={setPage} />
        <SplitActions>
          <Button variant="soft" size="sm" to="/recruiter/matching">
            Ghép hồ sơ
          </Button>
          <Button variant="ghost" size="sm" to="/recruiter/interviews">
            Phỏng vấn
          </Button>
        </SplitActions>
      </Panel>
    </RecruiterLayout>
  );
}
