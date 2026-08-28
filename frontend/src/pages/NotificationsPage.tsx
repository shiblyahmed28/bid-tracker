import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  fetchNotificationSettings,
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  updateNotificationSettings,
  type NotificationItem,
  type NotificationSettings,
} from "../api/notifications";
import { Skeleton } from "../dashboard/Skeleton";
import { formatFullDateTime } from "../lib/dateUtils";
import { notifyNotificationsChanged, subscribeNotificationsChanged } from "../lib/notificationBus";
import { ToggleRow } from "../components/ToggleRow";

const KIND_LABEL: Record<string, string> = {
  new_bid: "New bid",
  field_change: "Changed",
  deadline: "Deadline in 7 days",
};

function RecentNotifications({
  notifications,
  loading,
  onMarkAllRead,
  onOpen,
}: {
  notifications: NotificationItem[] | null;
  loading: boolean;
  onMarkAllRead: () => void;
  onOpen: (n: NotificationItem) => void;
}) {
  const unread = notifications?.filter((n) => !n.read).length ?? 0;

  return (
    <div className="card">
      <div className="chead">
        <h2>Recent notifications</h2>
        <span className="scope">{unread} unread</span>
        <div className="hgap" />
        <button className="btn btn-s btn-sm" onClick={onMarkAllRead} disabled={unread === 0}>
          Mark all read
        </button>
      </div>
      <div className="cbody">
        {loading ? (
          <Skeleton height={220} />
        ) : !notifications || notifications.length === 0 ? (
          <p className="hint">No notifications yet.</p>
        ) : (
          <ul className="tl">
            {notifications.map((n) => (
              <li key={n.id} onClick={() => onOpen(n)} style={{ cursor: n.bid || !n.read ? "pointer" : "default" }}>
                <div>
                  <b>{KIND_LABEL[n.kind] ?? n.kind}</b>
                  {!n.read && <span className="mini">new</span>} — {n.title}
                </div>
                {n.body && <div className="hint">{n.body}</div>}
                <time>{formatFullDateTime(n.created_at)}</time>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function DeliveryCard({
  settings,
  onChange,
}: {
  settings: NotificationSettings | null;
  onChange: (patch: Partial<NotificationSettings>) => void;
}) {
  if (!settings) {
    return (
      <div className="card">
        <div className="cbody">
          <Skeleton height={180} />
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="chead">
        <h2>Delivery</h2>
        <span className="scope">How you get alerted</span>
      </div>
      <div className="cbody">
        <ToggleRow
          label="Email — change digest"
          hint="One email per sync run covering everything you follow"
          checked={settings.email_digest}
          onChange={(v) => onChange({ email_digest: v })}
        />
        <ToggleRow
          label="Email — deadline alerts"
          hint="Sent immediately, 7 days before submission"
          checked={settings.email_deadline}
          onChange={(v) => onChange({ email_deadline: v })}
        />
        <ToggleRow
          label="Email — new bid created"
          hint="One alert with the bid title and submission date"
          checked={settings.email_newbid}
          onChange={(v) => onChange({ email_newbid: v })}
        />
        <ToggleRow
          label="Mute everything"
          hint="Overrides all of the above, including in-app"
          checked={settings.notifications_muted}
          onChange={(v) => onChange({ notifications_muted: v })}
        />
        <div className="banner b-info" style={{ margin: "14px 0 0" }}>
          Change emails are batched into one digest per sync run. Unbatched, a sync touching 40 bids across 15
          users would send 600 emails and hit Gmail's daily cap in one go.
        </div>
      </div>
    </div>
  );
}

function ColumnSubscriptions({
  settings,
  onToggleField,
}: {
  settings: NotificationSettings | null;
  onToggleField: (key: string, value: boolean) => void;
}) {
  if (!settings) {
    return (
      <div className="card">
        <div className="cbody">
          <Skeleton height={140} />
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="chead">
        <h2>Follow specific columns</h2>
        <span className="scope">Updates only</span>
        <div className="hgap" />
        <span className="hint">You are alerted only when a column you follow changes value</span>
      </div>
      <div className="cbody">
        <div className="colgrid">
          {Object.entries(settings.field_labels).map(([key, label]) => (
            <label className="colchk" key={key}>
              <input
                type="checkbox"
                checked={settings.fields[key] ?? false}
                onChange={(e) => onToggleField(key, e.target.checked)}
              />
              {label}
            </label>
          ))}
        </div>
        <p className="hint" style={{ marginTop: 11 }}>
          New bids always send exactly one alert regardless of these settings —{" "}
          <b>client — description · due date</b>.
        </p>
      </div>
    </div>
  );
}

export function NotificationsPage() {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<NotificationItem[] | null>(null);
  const [notifLoading, setNotifLoading] = useState(true);
  const [settings, setSettings] = useState<NotificationSettings | null>(null);

  const loadNotifications = useCallback(() => {
    setNotifLoading(true);
    fetchNotifications().then((page) => {
      setNotifications(page.results);
      setNotifLoading(false);
    });
  }, []);

  useEffect(() => {
    loadNotifications();
    fetchNotificationSettings().then(setSettings);
    return subscribeNotificationsChanged(loadNotifications);
  }, [loadNotifications]);

  function handleRead(id: number) {
    setNotifications((prev) => (prev ? prev.map((n) => (n.id === id ? { ...n, read: true } : n)) : prev));
    markNotificationRead(id).then(notifyNotificationsChanged);
  }

  function handleMarkAllRead() {
    setNotifications((prev) => (prev ? prev.map((n) => ({ ...n, read: true })) : prev));
    markAllNotificationsRead().then(notifyNotificationsChanged);
  }

  function handleOpen(n: NotificationItem) {
    if (!n.read) handleRead(n.id);
    if (n.bid) navigate(`/bids/${n.bid}`);
  }

  function handleSettingsChange(patch: Partial<NotificationSettings>) {
    setSettings((prev) => (prev ? { ...prev, ...patch } : prev));
    updateNotificationSettings(patch);
  }

  function handleFieldToggle(key: string, value: boolean) {
    setSettings((prev) => (prev ? { ...prev, fields: { ...prev.fields, [key]: value } } : prev));
    updateNotificationSettings({ fields: { [key]: value } });
  }

  return (
    <>
      <div className="grid c2">
        <RecentNotifications
          notifications={notifications}
          loading={notifLoading}
          onMarkAllRead={handleMarkAllRead}
          onOpen={handleOpen}
        />
        <DeliveryCard settings={settings} onChange={handleSettingsChange} />
      </div>
      <ColumnSubscriptions settings={settings} onToggleField={handleFieldToggle} />
    </>
  );
}
