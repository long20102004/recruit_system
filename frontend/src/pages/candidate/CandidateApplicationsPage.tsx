import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  MAX_PAGE_SIZE,
  applicationsApi,
  type ApplicationDto,
  type ApplicationHistoryDto,
} from "../../api/client";
import { SiteHeader } from "../../components/common";
import { useToast } from "../../context/ToastContext";
import { applicationBadge, initials, shortDate } from "../../utils/format";

/** Màn C06 · Đơn ứng tuyển của tôi (design canvas MyApplications.dc.html). */

const TABS: { key: string; label: string }[] = [
  { key: "ALL", label: "Tất cả" },
  { key: "SUBMITTED", label: "Đã nộp" },
  { key: "REVIEWING", label: "Đang xem xét" },
  { key: "INTERVIEW", label: "Phỏng vấn" },
  { key: "HIRED", label: "Trúng tuyển" },
  { key: "REJECTED", label: "Từ chối" },
  { key: "WITHDRAWN", label: "Đã rút" },
];

export function CandidateApplicationsPage() {
  const { toast } = useToast();
  const [apps, setApps] = useState<ApplicationDto[] | null>(null);
  const [tab, setTab] = useState("ALL");
  const [order, setOrder] = useState<"new" | "old">("new");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [openHistoryId, setOpenHistoryId] = useState<number | null>(null);
  const [historyMap, setHistoryMap] = useState<Record<number, ApplicationHistoryDto[]>>({});

  const load = useCallback(() => {
    applicationsApi.mine({ size: MAX_PAGE_SIZE })
      .then((p) => setApps(p.content))
      .catch((e) => { setApps([]); toast(e instanceof Error ? e.message : "Không tải được đơn ứng tuyển"); });
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleWithdraw(app: ApplicationDto) {
    setBusyId(app.id);
    try {
      await applicationsApi.withdraw(app.id);
      toast(`Đã rút đơn ứng tuyển vị trí “${app.jobTitle}”.`);
      setApps((prev) =>
        prev ? prev.map((x) => (x.id === app.id ? { ...x, status: "WITHDRAWN" } : x)) : prev
      );
      if (openHistoryId === app.id) {
        const h = await applicationsApi.history(app.id);
        setHistoryMap((m) => ({ ...m, [app.id]: h }));
      }
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không thể rút đơn ứng tuyển");
    } finally {
      setBusyId(null);
    }
  }

  async function toggleHistory(appId: number) {
    if (openHistoryId === appId) {
      setOpenHistoryId(null);
      return;
    }
    setOpenHistoryId(appId);
    if (!historyMap[appId]) {
      try {
        const items = await applicationsApi.history(appId);
        setHistoryMap((m) => ({ ...m, [appId]: items }));
      } catch (e) {
        toast(e instanceof Error ? e.message : "Không tải được lịch sử trạng thái");
      }
    }
  }

  const counts = useMemo(() => {
    const c: Record<string, number> = { ALL: apps?.length ?? 0 };
    for (const a of apps ?? []) c[a.status] = (c[a.status] ?? 0) + 1;
    return c;
  }, [apps]);

  const shown = useMemo(() => {
    const list = (apps ?? []).filter((a) => tab === "ALL" || a.status === tab);
    return [...list].sort((a, b) => {
      const d = (b.appliedAt ?? "").localeCompare(a.appliedAt ?? "");
      return order === "new" ? d : -d;
    });
  }, [apps, tab, order]);

  return (
    <>
      <SiteHeader active="applications" mode="candidate" />
      <div className="wrap" style={{ paddingTop: 32, paddingBottom: 64, display: "flex", flexDirection: "column", gap: 20 }}>
        <div className="page-head" style={{ marginBottom: 0 }}>
          <div>
            <h1 style={{ fontSize: 34 }}>Đơn ứng tuyển của tôi</h1>
            <p className="muted">Theo dõi trạng thái từng đơn. Trạng thái thay đổi khi nhà tuyển dụng xử lý đơn.</p>
          </div>
          <label className="row small" style={{ gap: 8 }}>
            <span className="muted">Sắp xếp</span>
            <select className="input" style={{ height: 38, width: "auto" }} value={order}
              onChange={(e) => setOrder(e.target.value as "new" | "old")}>
              <option value="new">Mới nộp nhất</option>
              <option value="old">Cũ nhất</option>
            </select>
          </label>
        </div>

        <div className="tabs" role="tablist" aria-label="Lọc theo trạng thái">
          {TABS.map((t) => (
            <button key={t.key} type="button" role="tab" aria-selected={tab === t.key}
              className={tab === t.key ? "tab tab-on" : "tab"} onClick={() => setTab(t.key)}>
              {t.label}<span className="count">{counts[t.key] ?? 0}</span>
            </button>
          ))}
        </div>

        {apps === null ? (
          <p className="muted">Đang tải…</p>
        ) : shown.length === 0 ? (
          <div className="card" style={{ textAlign: "center", padding: 40, background: "transparent", borderStyle: "dashed" }}>
            <p style={{ fontWeight: 650 }}>
              {apps.length === 0 ? "Bạn chưa nộp đơn nào." : "Chưa có đơn nào ở trạng thái này."}
            </p>
            <Link to="/candidate" className="btn btn-g btn-sm" style={{ marginTop: 12 }}>Tìm việc làm</Link>
          </div>
        ) : (
          <section className="card" style={{ padding: 0 }}>
            {shown.map((a) => {
              const b = applicationBadge(a.status);
              const st = (a.status ?? "").toUpperCase();
              const canWithdraw = st === "SUBMITTED" || st === "REVIEWING" || st === "INTERVIEW";
              const historyOpen = openHistoryId === a.id;
              const historyItems = historyMap[a.id] ?? [];
              return (
                <article key={a.id} style={{ padding: "18px 20px", borderBottom: "1px solid var(--line)" }}>
                  <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
                    <span className="logo logo-sm">{initials(a.companyName || a.jobTitle)}</span>
                    <div style={{ flex: "1 1 300px", minWidth: 0 }}>
                      <Link to={`/candidate/jobs/${a.jobId}`} style={{ fontWeight: 650, fontSize: 16 }}>{a.jobTitle}</Link>
                      <p className="small muted">
                        {a.companyName} · Nộp {shortDate(a.appliedAt)}
                        {a.coverLetter ? " · Có thư giới thiệu" : ""}
                      </p>
                    </div>
                    <div style={{ flex: "0 0 auto", display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
                      <span className={b.cls}>{b.label}</span>
                    </div>
                    <div className="row" style={{ gap: 8, flex: "0 0 auto" }}>
                      {st === "INTERVIEW" ? (
                        <Link to={`/candidate/interview?jobId=${a.jobId}`} className="btn btn-p btn-sm">Làm phỏng vấn</Link>
                      ) : null}
                      {canWithdraw ? (
                        <button
                          type="button"
                          className="btn btn-g btn-sm"
                          disabled={busyId === a.id}
                          onClick={() => void handleWithdraw(a)}
                        >
                          {busyId === a.id ? "Đang rút…" : "Rút đơn"}
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="btn btn-g btn-sm"
                        onClick={() => void toggleHistory(a.id)}
                      >
                        {historyOpen ? "Ẩn lịch sử" : "Lịch sử"}
                      </button>
                    </div>
                  </div>
                  {historyOpen ? (
                    <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px dashed var(--line)" }}>
                      {historyItems.length === 0 ? (
                        <p className="tiny muted">Chưa có lịch sử cập nhật trạng thái.</p>
                      ) : (
                        <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 4 }}>
                          {historyItems.map((item) => (
                            <li key={item.id} className="tiny">
                              <strong>{item.statusLabel}</strong> · {shortDate(item.timestamp)} · {item.actor}
                              {item.note ? ` — “${item.note}”` : ""}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ) : null}
                </article>
              );
            })}
          </section>
        )}
        {apps && apps.length >= MAX_PAGE_SIZE ? (
          <p className="help">Đang hiển thị {MAX_PAGE_SIZE} đơn gần nhất.</p>
        ) : null}
      </div>
    </>
  );
}
