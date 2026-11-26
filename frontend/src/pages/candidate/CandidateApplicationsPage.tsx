import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { MAX_PAGE_SIZE, applicationsApi, type ApplicationDto } from "../../api/client";
import { SiteHeader } from "../../components/common";
import { useToast } from "../../context/ToastContext";
import { applicationBadge, initials, shortDate } from "../../utils/format";

/** Màn C06 · Đơn ứng tuyển của tôi (design canvas MyApplications.dc.html), chỉ xem. */

const TABS: { key: string; label: string }[] = [
  { key: "ALL", label: "Tất cả" },
  { key: "SUBMITTED", label: "Đã nộp" },
  { key: "REVIEWING", label: "Đang xem xét" },
  { key: "INTERVIEW", label: "Phỏng vấn" },
  { key: "HIRED", label: "Trúng tuyển" },
  { key: "REJECTED", label: "Từ chối" },
];

export function CandidateApplicationsPage() {
  const { toast } = useToast();
  const [apps, setApps] = useState<ApplicationDto[] | null>(null);
  const [tab, setTab] = useState("ALL");
  const [order, setOrder] = useState<"new" | "old">("new");

  useEffect(() => {
    applicationsApi.mine({ size: MAX_PAGE_SIZE })
      .then((p) => setApps(p.content))
      .catch((e) => { setApps([]); toast(e instanceof Error ? e.message : "Không tải được đơn ứng tuyển"); });
  }, [toast]);

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
              return (
                <article key={a.id} style={{ display: "flex", gap: 16, padding: "18px 20px",
                  borderBottom: "1px solid var(--line)", flexWrap: "wrap", alignItems: "center" }}>
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
                  {a.status === "INTERVIEW" ? (
                    <div className="row" style={{ gap: 8, flex: "0 0 auto" }}>
                      <Link to={`/candidate/interview?jobId=${a.jobId}`} className="btn btn-p btn-sm">Làm phỏng vấn</Link>
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
