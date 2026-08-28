import { useCallback, useEffect, useState } from "react";

import {
  fetchOwnSessions,
  fetchUserSessions,
  fetchUsers,
  revokeOtherSessions,
  revokeSession,
  type AdminUser,
  type SessionItem,
} from "../api/accounts";
import { useAuth } from "../auth/AuthContext";
import { Modal } from "../components/Modal";
import { useToast } from "../components/ToastContext";
import { formatFullDateTime } from "../lib/dateUtils";
import { DesktopIcon, MobileIcon, TabletIcon } from "../icons";
import { Skeleton } from "../dashboard/Skeleton";

const DEVICE_ICON: Record<string, typeof DesktopIcon> = {
  desktop: DesktopIcon,
  mobile: MobileIcon,
  tablet: TabletIcon,
  unknown: DesktopIcon,
};

const DEVICE_LABEL: Record<string, string> = {
  desktop: "Desktop",
  mobile: "Mobile",
  tablet: "Tablet",
  unknown: "Unknown",
};

function statusTag(session: SessionItem) {
  if (session.is_current) return <span className="tag t-won">This device</span>;
  if (session.is_active) return <span className="tag t-sub">Signed in</span>;
  return <span className="tag t-no">Ended</span>;
}

export function SessionsPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const isAdmin = user?.role === "admin";

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [filterUserId, setFilterUserId] = useState<number | null>(null); // null = self
  const [rows, setRows] = useState<SessionItem[] | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    if (isAdmin) fetchUsers().then(setUsers);
  }, [isAdmin]);

  const load = useCallback(() => {
    setRows(null);
    const request = filterUserId === null ? fetchOwnSessions() : fetchUserSessions(filterUserId);
    request.then(setRows);
  }, [filterUserId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRevoke(id: number) {
    setBusyId(id);
    try {
      await revokeSession(id);
      load();
    } finally {
      setBusyId(null);
    }
  }

  async function handleSignOutOthers() {
    setShowConfirm(false);
    const result = await revokeOtherSessions();
    showToast(`Signed out ${result.revoked} other session(s)`);
    load();
  }

  if (rows === null) {
    return (
      <div className="card">
        <div className="cbody">
          <Skeleton height={260} />
        </div>
      </div>
    );
  }

  const viewingSelf = filterUserId === null;
  const activeCount = rows.filter((r) => r.is_active).length;
  const thirtyDaysAgo = Date.now() - 30 * 86_400_000;
  const recentCount = rows.filter((r) => new Date(r.created_at).getTime() >= thirtyDaysAgo).length;
  const lastSignIn = rows[0];

  return (
    <>
      {viewingSelf ? (
        <div className="banner b-info">
          You are seeing your own sign-in history. {isAdmin && "Admins can see every user's."}
        </div>
      ) : (
        <div className="banner b-ok">
          <b>Admin view.</b> Every user's sign-in history. Filter by user below.
        </div>
      )}

      <div className="grid kpis" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
        <div className="card kpi">
          <span className="klab">Active sessions</span>
          <b className="num kval">{activeCount}</b>
          <span className="ksub">signed in right now</span>
        </div>
        <div className="card kpi">
          <span className="klab">Sign-ins (30 days)</span>
          <b className="num kval">{recentCount}</b>
          <span className="ksub">successful</span>
        </div>
        <div className="card kpi">
          <span className="klab">Last sign-in</span>
          <b className="num kval">{lastSignIn ? formatFullDateTime(lastSignIn.created_at) : "—"}</b>
          <span className="ksub">{lastSignIn?.ip ?? "—"}</span>
        </div>
      </div>

      <div className="card">
        <div className="chead">
          <h2>Sign-in history</h2>
          <div className="hgap" />
          {isAdmin && (
            <select
              className="inp"
              style={{ width: "auto", padding: "6px 9px" }}
              value={filterUserId ?? "self"}
              onChange={(e) => setFilterUserId(e.target.value === "self" ? null : Number(e.target.value))}
            >
              <option value="self">Myself</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name || u.email}
                </option>
              ))}
            </select>
          )}
          {viewingSelf && (
            <button className="btn btn-d btn-sm" onClick={() => setShowConfirm(true)}>
              Sign out all other sessions
            </button>
          )}
        </div>
        <div className="tscroll">
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>IP address</th>
                <th>Device</th>
                <th>Browser</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => {
                const Icon = DEVICE_ICON[s.device_type];
                return (
                  <tr key={s.id}>
                    <td className="num" style={{ whiteSpace: "nowrap" }}>
                      {formatFullDateTime(s.created_at)}
                    </td>
                    <td className="num" style={{ fontSize: 11.5 }}>
                      {s.ip ?? "—"}
                    </td>
                    <td>
                      <span className="devi">
                        <Icon />
                        {DEVICE_LABEL[s.device_type]}
                      </span>
                      <br />
                      <span className="hint">{s.device_brand || s.os || "—"}</span>
                    </td>
                    <td>{s.browser || "—"}</td>
                    <td>{statusTag(s)}</td>
                    <td style={{ textAlign: "right" }}>
                      {s.is_active && !s.is_current && (
                        <button
                          className="btn btn-d btn-sm"
                          disabled={busyId === s.id}
                          onClick={() => handleRevoke(s.id)}
                        >
                          Sign out
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="cbody">
          <p className="hint">
            Device type, brand and browser are read from the user-agent string, so the brand is a best guess
            rather than a certainty. IP addresses are stored to help spot access from an unexpected network.
          </p>
        </div>
      </div>

      <Modal
        open={showConfirm}
        onClose={() => setShowConfirm(false)}
        title="Sign out all other sessions?"
        footer={
          <>
            <button className="btn btn-s" onClick={() => setShowConfirm(false)}>
              Cancel
            </button>
            <button className="btn btn-d" onClick={handleSignOutOthers}>
              Sign out other sessions
            </button>
          </>
        }
      >
        <p style={{ fontSize: 13, lineHeight: 1.6 }}>
          This immediately ends every session except the one you are using now. Anyone signed in on another
          device will have to sign in again.
        </p>
        <div className="banner b-warn" style={{ marginTop: 13 }}>
          {isAdmin
            ? "As an admin you can also revoke an individual session for any user from the table above."
            : "This affects only your own account."}
        </div>
      </Modal>
    </>
  );
}
