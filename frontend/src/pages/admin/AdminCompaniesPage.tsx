import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getToken } from "../../api/client";
import {
  approveCompany,
  listCompanies,
  lockCompany,
  rejectCompany,
  unlockCompany,
  type CompanyDto,
  type CompanyStatus,
} from "../../api/mock/companyMock";
import { EmptyNote, RecruiterLayout } from "../../components/common";
import { useToast } from "../../context/ToastContext";
import { shortDate } from "../../utils/format";

const STATUS_TABS: { key: CompanyStatus; label: string }[] = [
  { key: "PENDING", label: "Chờ duyệt" },
  { key: "ACTIVE", label: "Đang hoạt động" },
  { key: "REJECTED", label: "Bị từ chối" },
  { key: "LOCKED", label: "Bị khoá" },
];

const STATUS_BADGE: Record<CompanyStatus, { label: string; cls: string }> = {
  PENDING: { label: "Chờ duyệt", cls: "badge b-gold" },
  ACTIVE: { label: "Đang hoạt động", cls: "badge b-ok" },
  REJECTED: { label: "Bị từ chối", cls: "badge b-danger" },
  LOCKED: { label: "Bị khoá", cls: "badge b-danger" },
};

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${shortDate(iso)} ${hh}:${mm}`;
}

/** Màn AD02 · Duyệt và quản lý công ty (design canvas AdminCompanies.dc.html). */
export function AdminCompaniesPage() {
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedId = Number(searchParams.get("id") || 0) || null;

  const [companies, setCompanies] = useState<CompanyDto[] | null>(null);
  const [tab, setTab] = useState<CompanyStatus>("PENDING");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(requestedId);
  const [rejectReason, setRejectReason] = useState("");
  const [lockReason, setLockReason] = useState("");
  const [busy, setBusy] = useState(false);

  const loadCompanies = useCallback(async () => {
    try {
      const list = await listCompanies({ status: "ALL" });
      setCompanies(list);
    } catch (e: unknown) {
      setCompanies([]);
      toast(e instanceof Error ? e.message : "Không tải được danh sách công ty.");
    }
  }, [toast]);

  useEffect(() => {
    void loadCompanies();
  }, [loadCompanies]);

  useEffect(() => {
    if (!companies || !requestedId) return;
    const match = companies.find((c) => c.id === requestedId);
    if (match) {
      setTab(match.status);
      setSelectedId(match.id);
    }
  }, [companies, requestedId]);

  const counts = useMemo(() => {
    const map: Record<CompanyStatus, number> = { PENDING: 0, ACTIVE: 0, REJECTED: 0, LOCKED: 0 };
    for (const c of companies ?? []) map[c.status] += 1;
    return map;
  }, [companies]);

  const tabItems = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return (companies ?? []).filter((c) => {
      if (c.status !== tab) return false;
      if (!needle) return true;
      return `${c.name} ${c.legalName} ${c.taxCode}`.toLowerCase().includes(needle);
    });
  }, [companies, tab, query]);

  const selected = tabItems.find((c) => c.id === selectedId) ?? tabItems[0] ?? null;

  function selectCompany(companyId: number) {
    setSelectedId(companyId);
    setRejectReason("");
    setLockReason("");
    if (searchParams.has("id")) {
      setSearchParams({}, { replace: true });
    }
  }

  async function onApprove(company: CompanyDto) {
    setBusy(true);
    try {
      await approveCompany(company.id);
      toast(`Đã duyệt công ty ${company.name}`);
      setRejectReason("");
      await loadCompanies();
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : "Không duyệt được công ty.");
    } finally {
      setBusy(false);
    }
  }

  async function onReject(company: CompanyDto) {
    if (!rejectReason.trim()) {
      toast("Vui lòng nhập lý do từ chối.");
      return;
    }
    setBusy(true);
    try {
      await rejectCompany(company.id, rejectReason);
      toast(`Đã từ chối hồ sơ ${company.name}`);
      setRejectReason("");
      await loadCompanies();
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : "Không từ chối được công ty.");
    } finally {
      setBusy(false);
    }
  }

  async function onLock(company: CompanyDto) {
    setBusy(true);
    try {
      await lockCompany(company.id, lockReason);
      toast(`Đã khoá công ty ${company.name}`);
      setLockReason("");
      await loadCompanies();
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : "Không khoá được công ty.");
    } finally {
      setBusy(false);
    }
  }

  async function onUnlock(company: CompanyDto) {
    setBusy(true);
    try {
      await unlockCompany(company.id);
      toast(`Đã mở khoá công ty ${company.name}`);
      await loadCompanies();
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : "Không mở khoá được công ty.");
    } finally {
      setBusy(false);
    }
  }

  async function openLicense(company: CompanyDto) {
    try {
      const token = getToken();
      const res = await fetch(`/api/admin/companies/${company.id}/license`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!res.ok) {
        toast("Chưa có file giấy phép được tải lên cho công ty này.");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener,noreferrer");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch {
      toast("Không tải được file giấy phép.");
    }
  }

  const badge = selected ? STATUS_BADGE[selected.status] : null;

  return (
    <RecruiterLayout active="companies">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1 style={{ fontSize: 32 }}>Công ty</h1>
          <p className="muted">Duyệt hồ sơ đăng ký, khoá hoặc mở khoá công ty.</p>
        </div>
      </div>

      <div className="tabs" role="tablist" aria-label="Trạng thái công ty">
        {STATUS_TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            className={tab === t.key ? "tab tab-on" : "tab"}
            onClick={() => {
              setTab(t.key);
              setRejectReason("");
              setLockReason("");
            }}
          >
            {t.label}
            <span className="count">{counts[t.key]}</span>
          </button>
        ))}
      </div>

      {companies === null ? (
        <p className="muted">Đang tải danh sách công ty…</p>
      ) : (
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>
          <section className="card" style={{ flex: "1 1 320px", maxWidth: 400, padding: 0 }}>
            <div style={{ padding: 12 }}>
              <input
                className="input"
                type="search"
                placeholder="Tìm tên công ty, MST"
                aria-label="Tìm công ty theo tên hoặc mã số thuế"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>

            {tabItems.length === 0 ? (
              <div style={{ padding: 16 }}>
                <EmptyNote>Không có công ty nào khớp bộ lọc.</EmptyNote>
              </div>
            ) : (
              tabItems.map((c) => {
                const isSelected = selected?.id === c.id;
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => selectCompany(c.id)}
                    aria-current={isSelected ? "true" : undefined}
                    style={{
                      display: "flex",
                      gap: 12,
                      alignItems: "center",
                      padding: "12px 14px",
                      borderTop: "1px solid var(--line)",
                      borderLeft: 0,
                      borderRight: 0,
                      borderBottom: 0,
                      width: "100%",
                      textAlign: "left",
                      cursor: "pointer",
                      background: isSelected ? "var(--brand-soft)" : "transparent",
                      color: "inherit",
                      fontFamily: "inherit",
                    }}
                  >
                    <span className="logo logo-sm">{c.logo}</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontWeight: 650, fontSize: 14 }}>{c.name}</p>
                      <p className="tiny muted">
                        {c.industry} · gửi {shortDate(c.submittedAt)}
                      </p>
                    </div>
                  </button>
                );
              })
            )}
          </section>

          {selected && badge ? (
            <section
              className="card"
              style={{
                flex: "999 1 520px",
                minWidth: 0,
                padding: 26,
                display: "flex",
                flexDirection: "column",
                gap: 18,
              }}
            >
              <div className="row" style={{ gap: 16, flexWrap: "nowrap", alignItems: "flex-start" }}>
                <span className="logo logo-lg">{selected.logo}</span>
                <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 4 }}>
                  <div className="row" style={{ gap: 8 }}>
                    <h2 style={{ fontSize: 24 }}>{selected.name}</h2>
                    <span className={badge.cls}>{badge.label}</span>
                  </div>
                  <p className="small muted">
                    Gửi {formatDateTime(selected.submittedAt)} bởi {selected.submittedBy}
                  </p>
                </div>
              </div>

              <dl
                style={{
                  margin: 0,
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 240px), 1fr))",
                  gap: "14px 24px",
                  fontSize: 14,
                }}
              >
                <div>
                  <dt className="muted small">Tên pháp lý</dt>
                  <dd style={{ margin: "2px 0 0", fontWeight: 600 }}>{selected.legalName}</dd>
                </div>
                <div>
                  <dt className="muted small">Mã số thuế</dt>
                  <dd style={{ margin: "2px 0 0", fontWeight: 600 }}>{selected.taxCode}</dd>
                </div>
                <div>
                  <dt className="muted small">Lĩnh vực</dt>
                  <dd style={{ margin: "2px 0 0", fontWeight: 600 }}>{selected.industry}</dd>
                </div>
                <div>
                  <dt className="muted small">Quy mô</dt>
                  <dd style={{ margin: "2px 0 0", fontWeight: 600 }}>{selected.size}</dd>
                </div>
                <div>
                  <dt className="muted small">Website</dt>
                  <dd style={{ margin: "2px 0 0", fontWeight: 600 }}>{selected.website}</dd>
                </div>
                <div>
                  <dt className="muted small">Email</dt>
                  <dd style={{ margin: "2px 0 0", fontWeight: 600 }}>{selected.email}</dd>
                </div>
                <div>
                  <dt className="muted small">Điện thoại</dt>
                  <dd style={{ margin: "2px 0 0", fontWeight: 600 }}>{selected.phone}</dd>
                </div>
                <div>
                  <dt className="muted small">Địa chỉ</dt>
                  <dd style={{ margin: "2px 0 0", fontWeight: 600 }}>{selected.address}</dd>
                </div>
              </dl>

              <div>
                <p className="lbl" style={{ marginBottom: 8 }}>Giới thiệu</p>
                <p style={{ color: "var(--ink-soft)" }}>{selected.about}</p>
              </div>

              <div>
                <p className="lbl" style={{ marginBottom: 8 }}>Giấy phép kinh doanh</p>
                <div
                  style={{
                    display: "flex",
                    gap: 14,
                    alignItems: "center",
                    border: "1px solid var(--line)",
                    padding: 12,
                    background: "var(--surface)",
                  }}
                >
                  <div
                    style={{
                      width: 64,
                      height: 84,
                      background: "var(--sky)",
                      border: "1px solid var(--line)",
                      display: "grid",
                      placeItems: "center",
                    }}
                    className="tiny muted"
                  >
                    PDF
                  </div>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontWeight: 600 }}>{selected.licenseFile.name}</p>
                    <p className="tiny muted">{selected.licenseFile.meta}</p>
                  </div>
                  <button
                    type="button"
                    className="btn btn-g btn-sm"
                    onClick={() => void openLicense(selected)}
                  >
                    Mở file
                  </button>
                </div>
                <p className="help" style={{ marginTop: 6 }}>
                  Đối chiếu tên công ty và MST trên giấy phép với thông tin khai báo.
                </p>
              </div>

              <div style={{ borderTop: "1px solid var(--line)", paddingTop: 18, display: "flex", flexDirection: "column", gap: 12 }}>
                {selected.status === "PENDING" ? (
                  <>
                    <div className="field">
                      <label htmlFor="company-reject-reason">
                        Lý do từ chối (bắt buộc khi từ chối, gửi cho người đăng ký)
                      </label>
                      <textarea
                        id="company-reject-reason"
                        className="input"
                        placeholder="Ví dụ: Giấy phép không rõ nét, MST không khớp…"
                        style={{ minHeight: 80 }}
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                      />
                    </div>
                    <div className="row" style={{ justifyContent: "flex-end" }}>
                      <button
                        type="button"
                        className="btn btn-d"
                        disabled={busy}
                        onClick={() => void onReject(selected)}
                      >
                        Từ chối
                      </button>
                      <button
                        type="button"
                        className="btn btn-ok"
                        disabled={busy}
                        onClick={() => void onApprove(selected)}
                      >
                        Duyệt công ty
                      </button>
                    </div>
                  </>
                ) : selected.status === "ACTIVE" ? (
                  <>
                    <div className="field">
                      <label htmlFor="company-lock-reason">Lý do khoá công ty (tuỳ chọn)</label>
                      <input
                        id="company-lock-reason"
                        className="input"
                        placeholder="Ví dụ: Vi phạm quy định đăng tin tuyển dụng…"
                        value={lockReason}
                        onChange={(e) => setLockReason(e.target.value)}
                      />
                    </div>
                    <div className="between">
                      <Link to={`/companies/${selected.id}`} className="btn btn-g">
                        Xem trang công khai
                      </Link>
                      <button
                        type="button"
                        className="btn btn-d"
                        disabled={busy}
                        onClick={() => void onLock(selected)}
                      >
                        Khoá công ty
                      </button>
                    </div>
                  </>
                ) : selected.status === "LOCKED" ? (
                  <>
                    {selected.rejectReason ? (
                      <div className="note note-warn small">
                        <strong>Lý do khoá:</strong> {selected.rejectReason}
                      </div>
                    ) : null}
                    <div className="row" style={{ justifyContent: "flex-end" }}>
                      <button
                        type="button"
                        className="btn btn-ok"
                        disabled={busy}
                        onClick={() => void onUnlock(selected)}
                      >
                        Mở khoá công ty
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="note note-warn small">
                    <strong>Lý do từ chối:</strong> {selected.rejectReason || "Không có ghi chú."}
                  </div>
                )}
              </div>
            </section>
          ) : (
            <div style={{ flex: "999 1 520px" }}>
              <EmptyNote>Chọn một công ty ở danh sách bên trái để xem chi tiết.</EmptyNote>
            </div>
          )}
        </div>
      )}
    </RecruiterLayout>
  );
}
