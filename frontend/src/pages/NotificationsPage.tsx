import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  notificationsApi,
  type NotificationCategory,
  type NotificationDto,
} from "../api/client";
import { EmptyNote, RecruiterLayout, SiteHeader } from "../components/common";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { useNotificationStream } from "../hooks/useNotificationStream";
import { shortDate } from "../utils/format";

/** Màn C13 · Trung tâm thông báo (design canvas Notifications.dc.html), specs/009-notification-service. */

type NotifTab = "all" | "unread" | Exclude<NotificationCategory, "cv">;

const TABS: ReadonlyArray<{ key: NotifTab; label: string }> = [
  { key: "all", label: "Tất cả" },
  { key: "unread", label: "Chưa đọc" },
  { key: "application", label: "Ứng tuyển" },
  { key: "interview", label: "Phỏng vấn" },
  { key: "alert", label: "Job alert" },
  { key: "company", label: "Công ty" },
];

const CATEGORY_META: Record<NotificationCategory, { icon: string; iconCls: string }> = {
  application: { icon: "ĐƠN", iconCls: "b-brand" },
  interview: { icon: "PV", iconCls: "b-gold" },
  alert: { icon: "JA", iconCls: "b-ok" },
  company: { icon: "CT", iconCls: "b-brand" },
  cv: { icon: "CV", iconCls: "b-ok" },
};

const PAGE_SIZE = 10;

function listParams(tab: NotifTab, page: number) {
  return {
    category: tab !== "all" && tab !== "unread" ? tab : undefined,
    unread: tab === "unread" ? true : undefined,
    page,
    size: PAGE_SIZE,
  };
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${shortDate(iso)} ${hh}:${mm}`;
}

function isInternalLink(link: string | null): link is string {
  return !!link && link.startsWith("/") && !link.startsWith("//") && !link.startsWith("/\\");
}

function matchesTab(dto: NotificationDto, tab: NotifTab): boolean {
  if (tab === "all") return true;
  if (tab === "unread") return !dto.read;
  return dto.category === tab;
}

export function NotificationsPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [items, setItems] = useState<NotificationDto[] | null>(null);
  const [tab, setTab] = useState<NotifTab>("all");
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const [busyAll, setBusyAll] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([
      notificationsApi.list(listParams(tab, 0)),
      notificationsApi.unreadCount(),
    ])
      .then(([pageRes, unreadRes]) => {
        if (!active) return;
        setItems(pageRes.content);
        setPage(pageRes.pageNumber);
        setHasMore(!pageRes.last);
        setUnreadCount(unreadRes.count);
      })
      .catch((e) => {
        if (!active) return;
        setItems([]);
        setHasMore(false);
        toast(e instanceof Error ? e.message : "Không tải được thông báo");
      });
    return () => {
      active = false;
    };
  }, [tab, toast]);

  const handleStreamNotification = useCallback(
    (dto: NotificationDto) => {
      if (!matchesTab(dto, tab)) return;
      setItems((prev) => {
        if (!prev) return [dto];
        if (prev.some((x) => x.id === dto.id)) return prev;
        return [dto, ...prev];
      });
    },
    [tab]
  );

  useNotificationStream({
    enabled: !!user,
    onNotification: handleStreamNotification,
    onUnread: setUnreadCount,
  });

  function onSelectTab(next: NotifTab) {
    if (next === tab) return;
    setTab(next);
    setPage(0);
    setHasMore(false);
    setItems(null);
  }

  async function onLoadMore() {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const pageRes = await notificationsApi.list(listParams(tab, nextPage));
      setItems((prev) => {
        const existing = prev ?? [];
        const seen = new Set(existing.map((x) => x.id));
        const appended = pageRes.content.filter((x) => !seen.has(x.id));
        return [...existing, ...appended];
      });
      setPage(pageRes.pageNumber);
      setHasMore(!pageRes.last && pageRes.content.length > 0);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không tải thêm được thông báo");
    } finally {
      setLoadingMore(false);
    }
  }

  async function onMarkRead(item: NotificationDto) {
    if (item.read) return;
    try {
      const updated = await notificationsApi.markRead(item.id);
      setItems((prev) =>
        prev ? prev.map((n) => (n.id === updated.id ? updated : n)) : prev
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không thể đánh dấu đã đọc");
    }
  }

  async function onItemClick(item: NotificationDto) {
    if (!item.read) {
      await onMarkRead(item);
    }
    if (isInternalLink(item.link)) {
      navigate(item.link);
    }
  }

  async function onMarkAllRead() {
    setBusyAll(true);
    try {
      const res = await notificationsApi.markAllRead();
      setItems((prev) => (prev ? prev.map((n) => ({ ...n, read: true })) : prev));
      setUnreadCount(res.count);
      toast("Đã đánh dấu đọc tất cả thông báo.");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không thể đánh dấu tất cả");
    } finally {
      setBusyAll(false);
    }
  }

  const isRecruiterOrAdmin = user?.role === "RECRUITER" || user?.role === "ADMIN";

  const content = (
    <>
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
      ) : items.length === 0 ? (
        <EmptyNote>
          {tab === "unread"
            ? "Bạn đã đọc hết tất cả thông báo."
            : "Chưa có thông báo nào trong mục này."}
        </EmptyNote>
      ) : (
        <section className="card" style={{ padding: 0 }}>
          {items.map((n) => {
            const meta = CATEGORY_META[n.category] ?? { icon: "TB", iconCls: "b-plain" };
            const internalLink = isInternalLink(n.link);
            const unread = !n.read;
            return (
              <article
                key={n.id}
                onClick={() => void onItemClick(n)}
                style={{
                  display: "flex",
                  gap: 14,
                  alignItems: "flex-start",
                  padding: "18px 20px",
                  borderBottom: "1px solid var(--line)",
                  flexWrap: "wrap",
                  background: unread ? "var(--brand-soft)" : undefined,
                  cursor: unread || internalLink ? "pointer" : "default",
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
                    background: unread ? "var(--brand)" : "transparent",
                  }}
                />
                <span
                  className={meta.iconCls}
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
                  {meta.icon}
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
                  {n.body ? (
                    <p className="small" style={{ color: "var(--ink-soft)" }}>
                      {n.body}
                    </p>
                  ) : null}
                  {internalLink ? (
                    <Link
                      to={n.link!}
                      className="btn-link tiny"
                      style={{ alignSelf: "flex-start", marginTop: 2 }}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (unread) void onMarkRead(n);
                      }}
                    >
                      Xem chi tiết →
                    </Link>
                  ) : null}
                </div>

                <span className="tiny muted" style={{ flex: "none" }}>
                  {formatTime(n.createdAt)}
                </span>
              </article>
            );
          })}
        </section>
      )}

      {hasMore ? (
        <button
          type="button"
          className="btn btn-g"
          style={{ alignSelf: "center" }}
          disabled={loadingMore}
          onClick={onLoadMore}
        >
          {loadingMore ? "Đang tải…" : "Xem thêm"}
        </button>
      ) : null}
    </>
  );

  if (isRecruiterOrAdmin) {
    return (
      <RecruiterLayout active="notifications">
        <div
          style={{
            maxWidth: 880,
            width: "100%",
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}
        >
          {content}
        </div>
      </RecruiterLayout>
    );
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
        {content}
      </div>
    </>
  );
}
