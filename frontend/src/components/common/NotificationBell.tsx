import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { notificationsApi, type NotificationDto } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { useNotificationStream } from "../../hooks/useNotificationStream";
import { classNames, shortDate } from "../../utils/format";

interface NotificationBellProps {
  enabled: boolean;
  active?: boolean;
}

const POPOVER_LIMIT = 5;

function isInternalLink(link: string | null): link is string {
  return !!link && link.startsWith("/") && !link.startsWith("//") && !link.startsWith("/\\");
}

function formatRelativeTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const now = new Date();
  const diffMin = Math.floor((now.getTime() - d.getTime()) / 60_000);
  if (diffMin < 1) return "Vừa xong";
  if (diffMin < 60) return `${diffMin} phút trước`;
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  const diffHours = Math.floor(diffMin / 60);
  if (sameDay && diffHours < 12) return `${diffHours} giờ trước`;
  if (sameDay) return `Hôm nay ${hh}:${mm}`;
  return `${shortDate(iso)} ${hh}:${mm}`;
}

export function NotificationBell({ enabled, active = false }: NotificationBellProps) {
  const navigate = useNavigate();
  const { toast } = useToast();
  const wrapRef = useRef<HTMLDivElement>(null);

  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState<NotificationDto[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [busyAll, setBusyAll] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    notificationsApi
      .unreadCount()
      .then((r) => {
        if (alive) setUnread(r.count);
      })
      .catch(() => {
        if (alive) setUnread(0);
      });
    return () => {
      alive = false;
    };
  }, [enabled]);

  const handleStreamNotification = useCallback((dto: NotificationDto) => {
    setItems((prev) => {
      if (prev === null) return prev;
      if (prev.some((x) => x.id === dto.id)) return prev;
      return [dto, ...prev].slice(0, POPOVER_LIMIT);
    });
  }, []);

  useNotificationStream({
    enabled,
    onUnread: setUnread,
    onNotification: handleStreamNotification,
  });

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  function toggle() {
    if (!enabled) return;
    const next = !open;
    setOpen(next);
    if (!next) return;
    setLoading(true);
    notificationsApi
      .list({ page: 0, size: POPOVER_LIMIT })
      .then((res) => setItems(res.content.slice(0, POPOVER_LIMIT)))
      .catch((e) => {
        setItems([]);
        toast(e instanceof Error ? e.message : "Không tải được thông báo");
      })
      .finally(() => setLoading(false));
  }

  async function onMarkAllRead() {
    if (busyAll || unread === 0) return;
    setBusyAll(true);
    try {
      const res = await notificationsApi.markAllRead();
      setUnread(res.count);
      setItems((prev) => (prev ? prev.map((n) => ({ ...n, read: true })) : prev));
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không thể đánh dấu đọc tất cả");
    } finally {
      setBusyAll(false);
    }
  }

  async function onItemClick(item: NotificationDto) {
    if (!item.read) {
      try {
        const updated = await notificationsApi.markRead(item.id);
        setItems((prev) =>
          prev ? prev.map((n) => (n.id === updated.id ? updated : n)) : prev
        );
        setUnread((c) => Math.max(0, c - 1));
      } catch (e) {
        toast(e instanceof Error ? e.message : "Không thể đánh dấu đã đọc");
      }
    }
    setOpen(false);
    navigate(isInternalLink(item.link) ? item.link : "/notifications");
  }

  const displayUnread = enabled ? unread : 0;
  const isOpen = enabled && open;

  return (
    <div ref={wrapRef} className="notif-bell-wrap">
      <button
        type="button"
        className={classNames("icon-btn notif-bell-btn", (isOpen || active) && "is-active")}
        aria-label={displayUnread > 0 ? `Thông báo, ${displayUnread} chưa đọc` : "Thông báo"}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        onClick={toggle}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
          <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
        </svg>
        {displayUnread > 0 ? (
          <span className="count notif-bell-count">{displayUnread > 99 ? "99+" : displayUnread}</span>
        ) : null}
      </button>

      {isOpen ? (
        <div className="notif-popover" role="dialog" aria-label="Thông báo gần đây">
          <div className="notif-pop-head">
            <span className="notif-pop-title">Thông báo</span>
            <button
              type="button"
              className="notif-pop-action"
              disabled={displayUnread === 0 || busyAll}
              onClick={() => void onMarkAllRead()}
            >
              Đọc tất cả
            </button>
          </div>

          {loading && items === null ? (
            <p className="notif-pop-empty">Đang tải thông báo…</p>
          ) : !items || items.length === 0 ? (
            <p className="notif-pop-empty">Chưa có thông báo nào.</p>
          ) : (
            <ul className="notif-pop-list">
              {items.map((item) => {
                const unreadItem = !item.read;
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      className={classNames("notif-pop-item", unreadItem && "is-unread")}
                      onClick={() => void onItemClick(item)}
                    >
                      <span className="notif-pop-dot" aria-hidden="true" />
                      <span className="notif-pop-item-body">
                        <span className="notif-pop-item-title">{item.title}</span>
                        <span className="notif-pop-time">{formatRelativeTime(item.createdAt)}</span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}

          <Link to="/notifications" className="notif-pop-footer" onClick={() => setOpen(false)}>
            Xem tất cả thông báo
          </Link>
        </div>
      ) : null}
    </div>
  );
}
