import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type NotificationItem,
} from "../../api/notifications";
import { formatFullDateTime } from "../../lib/dateUtils";
import { notifyNotificationsChanged, subscribeNotificationsChanged } from "../../lib/notificationBus";
import { BellIcon } from "../../icons";

const POLL_MS = 60_000;
const PREVIEW_COUNT = 6;

export function NotificationBell() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const load = () => fetchNotifications().then((page) => setItems(page.results));

  useEffect(() => {
    load();
    const interval = setInterval(load, POLL_MS);
    const unsubscribe = subscribeNotificationsChanged(load);
    return () => {
      clearInterval(interval);
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const unreadCount = items.filter((n) => !n.read).length;

  function handleRead(id: number) {
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
    markNotificationRead(id).then(notifyNotificationsChanged);
  }

  function handleMarkAllRead() {
    setItems((prev) => prev.map((n) => ({ ...n, read: true })));
    markAllNotificationsRead().then(notifyNotificationsChanged);
  }

  return (
    <div className="bell-wrap" ref={containerRef}>
      <button className="bell" aria-label="Notifications" onClick={() => setOpen((v) => !v)}>
        <BellIcon />
        {unreadCount > 0 && <b>{unreadCount > 9 ? "9+" : unreadCount}</b>}
      </button>
      {open && (
        <div className="bell-panel">
          <div className="bell-panel-head">
            <b>Notifications</b>
            <div className="hgap" />
            <button className="btn btn-s btn-sm" onClick={handleMarkAllRead} disabled={unreadCount === 0}>
              Mark all read
            </button>
          </div>
          <div className="bell-panel-list">
            {items.length === 0 ? (
              <p className="hint" style={{ padding: 14 }}>
                No notifications yet.
              </p>
            ) : (
              items.slice(0, PREVIEW_COUNT).map((n) => (
                <div
                  key={n.id}
                  className={`bell-item${n.read ? "" : " unread"}`}
                  onClick={() => !n.read && handleRead(n.id)}
                >
                  <div className="bell-item-title">{n.title}</div>
                  <time>{formatFullDateTime(n.created_at)}</time>
                </div>
              ))
            )}
          </div>
          <div className="bell-panel-foot">
            <Link to="/notifications" onClick={() => setOpen(false)}>
              View all notifications
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
