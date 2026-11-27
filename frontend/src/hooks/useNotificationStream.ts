import { useEffect, useRef } from "react";
import {
  getToken,
  notificationsApi,
  type NotificationDto,
  type UnreadCountDto,
} from "../api/client";

export interface UseNotificationStreamOptions {
  enabled?: boolean;
  onNotification?: (dto: NotificationDto) => void;
  onUnread?: (count: number) => void;
}

const INITIAL_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 30_000;

/**
 * Kết nối SSE `/api/notifications/stream` bằng fetch (gửi Bearer token) và tự nối lại
 * với exponential backoff khi mất mạng, dừng nếu server trả 401/403.
 */
export function useNotificationStream({
  enabled = true,
  onNotification,
  onUnread,
}: UseNotificationStreamOptions): void {
  const onNotificationRef = useRef(onNotification);
  const onUnreadRef = useRef(onUnread);

  useEffect(() => {
    onNotificationRef.current = onNotification;
    onUnreadRef.current = onUnread;
  }, [onNotification, onUnread]);

  useEffect(() => {
    if (!enabled) return;
    if (!getToken()) return;

    let cancelled = false;
    let controller: AbortController | null = null;
    let retryTimer: number | null = null;
    let attempt = 0;

    function dispatchEvent(rawBlock: string) {
      let eventName = "message";
      const dataLines: string[] = [];

      for (const line of rawBlock.split("\n")) {
        if (!line || line.startsWith(":")) continue;
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).replace(/^ /, ""));
        }
      }

      if (eventName === "ping" || dataLines.length === 0) return;
      const payload = dataLines.join("\n");

      try {
        if (eventName === "notification") {
          const dto = JSON.parse(payload) as NotificationDto;
          onNotificationRef.current?.(dto);
        } else if (eventName === "unread") {
          const data = JSON.parse(payload) as UnreadCountDto;
          if (typeof data?.count === "number") {
            onUnreadRef.current?.(data.count);
          }
        }
      } catch {
        // Bỏ qua frame JSON không hợp lệ để không làm đứt stream.
      }
    }

    function scheduleReconnect() {
      if (cancelled) return;
      const delay = Math.min(INITIAL_BACKOFF_MS * 2 ** attempt, MAX_BACKOFF_MS);
      attempt += 1;
      retryTimer = window.setTimeout(() => {
        if (!cancelled) void connect();
      }, delay);
    }

    async function connect() {
      const token = getToken();
      if (!token || cancelled) return;

      controller = new AbortController();
      let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

      try {
        const res = await fetch(notificationsApi.streamUrl(), {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "text/event-stream",
          },
          signal: controller.signal,
        });

        if (res.status === 401 || res.status === 403) {
          return;
        }

        if (!res.ok || !res.body) {
          scheduleReconnect();
          return;
        }

        attempt = 0;
        reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (!cancelled) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          buffer = buffer.replace(/\r\n/g, "\n");

          let sep = buffer.indexOf("\n\n");
          while (sep !== -1) {
            const rawBlock = buffer.slice(0, sep);
            buffer = buffer.slice(sep + 2);
            if (rawBlock.trim()) dispatchEvent(rawBlock);
            sep = buffer.indexOf("\n\n");
          }
        }

        if (!cancelled) {
          scheduleReconnect();
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof DOMException && err.name === "AbortError") return;
        scheduleReconnect();
      } finally {
        if (reader) {
          reader.releaseLock();
        }
      }
    }

    void connect();

    return () => {
      cancelled = true;
      if (retryTimer !== null) window.clearTimeout(retryTimer);
      controller?.abort();
    };
  }, [enabled]);
}
