import { useEffect, useState } from "react";

import type { AdminUser } from "../api/accounts";
import {
  clearUserCapability,
  fetchUserCapabilities,
  setUserCapability,
  type CapabilitiesReference,
  type EffectiveCapability,
} from "../api/settings";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/ToastContext";
import { Skeleton } from "../dashboard/Skeleton";

const CAPABILITY_LABELS: Record<string, string> = {
  access_master_settings: "Master settings",
  manage_users: "Manage users",
  view_audit_log: "Audit log",
  view_sync_history: "Sync history",
  trigger_sync: "Trigger sync",
  manage_choice_lists: "Manage lists",
  manage_notification_policy: "Notification policy",
  delete_bid: "Delete bid",
  export_pdf: "Export PDF",
  create_bid: "Create bid",
  edit_bid: "Edit bid",
};

const SELF_LOCKOUT_PROTECTED = new Set(["manage_users", "access_master_settings"]);

interface CapabilityMatrixProps {
  users: AdminUser[];
  reference: CapabilitiesReference;
}

export function CapabilityMatrix({ users, reference }: CapabilityMatrixProps) {
  const { user: currentUser, refreshUser } = useAuth();
  const { showToast } = useToast();
  const [rows, setRows] = useState<Record<number, EffectiveCapability[]> | null>(null);
  const [busyCell, setBusyCell] = useState<string | null>(null);

  useEffect(() => {
    Promise.all(users.map((u) => fetchUserCapabilities(u.id))).then((results) => {
      const byUser: Record<number, EffectiveCapability[]> = {};
      results.forEach((r, i) => {
        byUser[users[i].id] = r.effective;
      });
      setRows(byUser);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [users]);

  if (rows === null) {
    return <Skeleton height={220} />;
  }

  function cellFor(userId: number, capability: string): EffectiveCapability {
    return rows![userId].find((c) => c.capability === capability)!;
  }

  function isSelfLockoutRisk(userId: number, capability: string, nextGranted: boolean | null) {
    if (userId !== currentUser?.id) return false;
    if (!SELF_LOCKOUT_PROTECTED.has(capability)) return false;
    // nextGranted === null means "clear override -> role default"
    if (nextGranted === false) return true;
    return false;
  }

  async function handleClick(user: AdminUser, capability: string) {
    const cell = cellFor(user.id, capability);
    const cellKey = `${user.id}:${capability}`;

    // Cycle: role_default -> granted(true) -> revoked(false) -> role_default
    let action: "grant" | "revoke" | "clear";
    let nextGrantedForGuard: boolean | null;
    if (cell.source === "role_default") {
      action = "grant";
      nextGrantedForGuard = true;
    } else if (cell.source === "override" && cell.granted) {
      action = "revoke";
      nextGrantedForGuard = false;
    } else {
      action = "clear";
      nextGrantedForGuard = null;
    }

    if (isSelfLockoutRisk(user.id, capability, nextGrantedForGuard)) return;

    setBusyCell(cellKey);
    try {
      const result =
        action === "clear"
          ? await clearUserCapability(user.id, capability)
          : await setUserCapability(user.id, capability, action === "grant");

      setRows((prev) => ({ ...prev, [user.id]: result.effective }));
      showToast(`${CAPABILITY_LABELS[capability] ?? capability} ${action === "clear" ? "reset" : action + "ed"} for ${user.full_name || user.email}`);
      if (user.id === currentUser?.id) refreshUser();
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? "Could not update that capability.");
    } finally {
      setBusyCell(null);
    }
  }

  return (
    <div className="tscroll">
      <table className="matrix-table">
        <thead>
          <tr>
            <th className="sticky-col">User</th>
            {reference.capabilities.map((cap) => (
              <th key={cap}>{CAPABILITY_LABELS[cap] ?? cap}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <td className="sticky-col">
                <b>{user.full_name || user.email}</b>
                <br />
                <span className="hint">{user.role}</span>
              </td>
              {reference.capabilities.map((cap) => {
                const cell = cellFor(user.id, cap);
                const cellKey = `${user.id}:${cap}`;
                const disabled =
                  busyCell === cellKey ||
                  isSelfLockoutRisk(
                    user.id,
                    cap,
                    cell.source === "role_default" ? true : cell.granted ? false : null
                  );
                const stateClass = cell.source === "role_default" ? "inherited" : cell.granted ? "granted" : "revoked";
                return (
                  <td key={cap} style={{ textAlign: "center" }}>
                    <button
                      className={`cap-cell cap-${stateClass}`}
                      disabled={disabled}
                      title={
                        cell.source === "role_default"
                          ? `Inherited from ${user.role} role (${cell.granted ? "on" : "off"})`
                          : cell.granted
                            ? "Explicitly granted"
                            : "Explicitly revoked"
                      }
                      onClick={() => handleClick(user, cap)}
                    >
                      {cell.source === "role_default" ? (cell.granted ? "•" : "·") : cell.granted ? "✓" : "✗"}
                    </button>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
