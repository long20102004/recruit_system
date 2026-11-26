import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyNote, MockNote, SiteHeader } from "../components/common";
import {
  notificationsMock,
  type NotificationCategory,
  type NotificationItem,
} from "../api/mock/candidateMock";
import { useToast } from "../context/ToastContext";

/** Màn C13 · Trung tâm thông báo (design canvas Notifications.dc.html). */

type NotifTab = "all" | "unread" | Exclude<NotificationCategory, "cv">;

const TABS: ReadonlyArray<{ key: NotifTab; label: string }> = [
  { key: "all", label: "Tất cả" },
  { key: "unread", label: "Chưa đọc" },
  { key: "application", label: "Ứng tuyển" },
  { key: "interview", label: "Phỏng vấn" },
  { key: "alert", label: "Job alert" },
  { key: "company", label: "Công ty" },
];

const PAGE_SIZE = 6;

export function NotificationsPage() {
  const { toast } = useToast();
  const [items, setItems] = useState<NotificationItem[] | null>(null);
  const [tab, setTab] = useState<NotifTab>("all");
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [busyAll, setBusyAll] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    notificationsMock
      .list()
      .then(setItems)
      .catch((e) => {
        setItems([]);
        toast(e instanceof Error ? e.message : "Không tải được thông báo");
      });
  }, [toast]);

  const unreadCount = useMemo(
    () => (items ?? []).filter((n) => n.unread).length,
    [items]
  );

  const filtered = useMemo(() => {
    const list = items ?? [];
    if (tab === "all") return list;
    if (tab === "unread") return list.filter((n) => n.unread);
    return list.filter((n) => n.category === tab);
  }, [items, tab]);

  const visibleItems = filtered.slice(0, visibleCount);
  const hasMore = filtered.length > visibleCount;

  function onSelectTab(next: NotifTab) {
    setTab(next);
    setVisibleCount(PAGE_SIZE);
  }

  async function onMarkRead(item: NotificationItem) {
    if (!item.unread) return;
    try {
      const updated = await notificationsMock.markRead(item.id);
      setItems((prev) =>
        prev ? prev.map((n) => (n.id === updated.id ? updated : n)) : prev
      );
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không thể đánh dấu đã đọc");
    }
  }

  async function onMarkAllRead() {
    setBusyAll(true);
    try {
      await notificationsMock.markAllRead();
      setItems((prev) => (prev ? prev.map((n) => ({ ...n, unread: false })) : prev));
      toast("Đã đánh dấu đọc tất cả thông báo.");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không thể đánh dấu tất cả");
    } finally {
      setBusyAll(false);
    }
  }

  async function onRespondInvite(
    item: NotificationItem,
    decision: "accepted" | "declined"
  ) {
    setBusyId(item.id);
    try {
      const updated = await notificationsMock.respondInvite(item.id, decision);
      setItems((prev) =>
        prev ? prev.map((n) => (n.id === updated.id ? updated : n)) : prev
      );
      toast(
        decision === "accepted"
          ? "Đã chấp nhận lời mời tham gia công ty."
          : "Đã từ chối lời mời tham gia công ty."
      );
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không thể xử lý lời mời");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <SiteHeader active="notifications" mode="candidate" />
      <div
        className="wrap"
        style={{
          paddingTop: 32,
          paddingBottom: 64,
          maxWidth: 880,
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        <MockNote />

        <div className="page-head" style={{ marginBottom: 0 }}>
          <div>
            <h1 style={{ fontSize: 34 }}>Thông báo</h1>
            <p className="muted">{unreadCount} chưa đọc</p>
          </div>
          <div className="row">
            <button
              type="button"
              className="btn btn-g btn-sm"
              disabled={unreadCount === 0 || busyAll}
              onClick={onMarkAllRead}
            >
              Đánh dấu đã đọc tất cả
            </button>
            <Link to="/candidate/profile#notif" className="btn btn-g btn-sm">
              Cài đặt thông báo
            </Link>
          </div>
        </div>

        <div className="tabs" role="tablist" aria-label="Lọc thông báo">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              role="tab"
              aria-selected={tab === t.key}
              className={tab === t.key ? "tab tab-on" : "tab"}
              onClick={() => onSelectTab(t.key)}
            >
              {t.label}
              {t.key === "unread" ? <span className="count">{unreadCount}</span> : null}
            </button>
          ))}
        </div>

        {items === null ? (
          <p className="muted">Đang tải…</p>
        ) : visibleItems.length === 0 ? (
          <EmptyNote>
            {tab === "unread"
              ? "Bạn đã đọc hết tất cả thông báo."
              : "Chưa có thông báo nào trong mục này."}
          </EmptyNote>
        ) : (
          <section className="card" style={{ padding: 0 }}>
            {visibleItems.map((n) => (
              <article
                key={n.id}
                onClick={() => onMarkRead(n)}
                style={{
                  display: "flex",
                  gap: 14,
                  alignItems: "flex-start",
                  padding: "18px 20px",
                  borderBottom: "1px solid var(--line)",
                  flexWrap: "wrap",
                  background: n.unread ? "var(--brand-soft)" : undefined,
                  cursor: n.unread ? "pointer" : "default",
                }}
              >
                <span
                  aria-hidden="true"
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    marginTop: 16,
                    flex: "none",
                    background: n.unread ? "var(--brand)" : "transparent",
                  }}
                />
                <span
                  className={n.iconCls}
                  style={{
                    width: 40,
                    height: 40,
                    display: "grid",
                    placeItems: "center",
                    borderRadius: "50%",
                    flex: "none",
                    fontWeight: 700,
                    fontSize: 13,
                  }}
                >
                  {n.icon}
                </span>

                <div
                  style={{
                    flex: "1 1 320px",
                    minWidth: 0,
                    display: "flex",
                    flexDirection: "column",
                    gap: 4,
                  }}
                >
                  <p style={{ fontWeight: 650, fontSize: 14.5 }}>{n.title}</p>
                  <p className="small" style={{ color: "var(--ink-soft)" }}>
                    {n.body}
                  </p>

                  {n.isInvite ? (
                    <div
                      className="row"
                      style={{ gap: 8, marginTop: 6 }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {n.inviteStatus === "accepted" ? (
                        <span className="badge b-ok">Đã chấp nhận</span>
                      ) : n.inviteStatus === "declined" ? (
                        <span className="badge b-plain">Đã từ chối</span>
                      ) : (
                        <>
                          <button
                            type="button"
                            className="btn btn-p btn-sm"
                            disabled={busyId === n.id}
                            onClick={() => onRespondInvite(n, "accepted")}
                          >
                            Chấp nhận
                          </button>
                          <button
                            type="button"
                            className="btn btn-g btn-sm"
                            disabled={busyId === n.id}
                            onClick={() => onRespondInvite(n, "declined")}
                          >
                            Từ chối
                          </button>
                          {n.inviteExpiry ? (
                            <span className="tiny muted">{n.inviteExpiry}</span>
                          ) : null}
                        </>
                      )}
                    </div>
                  ) : null}
                </div>

                <span className="tiny muted" style={{ flex: "none" }}>
                  {n.time}
                </span>
              </article>
            ))}
          </section>
        )}

        {hasMore ? (
          <button
            type="button"
            className="btn btn-g"
            style={{ alignSelf: "center" }}
            onClick={() => setVisibleCount((c) => c + PAGE_SIZE)}
          >
            Xem thêm
          </button>
        ) : null}
      </div>
    </>
  );
}
