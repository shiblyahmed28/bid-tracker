import { useEffect, useState } from "react";

import { fetchUsers, updateUser, type AdminUser } from "../api/accounts";
import { fetchCapabilitiesReference, type CapabilitiesReference } from "../api/settings";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/ToastContext";
import { Skeleton } from "../dashboard/Skeleton";
import { CapabilityMatrix } from "./CapabilityMatrix";

const ROLE_LABEL: Record<string, string> = { admin: "Admin", editor: "Editor", viewer: "Viewer" };
const ROLES = ["viewer", "editor", "admin"] as const;

export function PermissionsTab() {
  const { user: currentUser } = useAuth();
  const { showToast } = useToast();
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [reference, setReference] = useState<CapabilitiesReference | null>(null);

  function load() {
    fetchUsers().then(setUsers);
  }

  useEffect(() => {
    load();
    fetchCapabilitiesReference().then(setReference);
  }, []);

  async function handleRoleChange(user: AdminUser, role: string) {
    try {
      const updated = await updateUser(user.id, { role: role as AdminUser["role"] });
      setUsers((prev) => (prev ? prev.map((u) => (u.id === user.id ? updated : u)) : prev));
      showToast(`${updated.full_name || updated.email} is now ${ROLE_LABEL[role]}`);
    } catch (err: any) {
      showToast(err?.response?.data?.role?.[0] ?? err?.response?.data?.detail ?? "Could not change role.");
    }
  }

  if (users === null || reference === null) {
    return (
      <div className="card">
        <div className="cbody">
          <Skeleton height={260} />
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="card">
        <div className="chead">
          <h2>Users</h2>
          <span className="scope">Role controls the baseline</span>
        </div>
        <div className="tscroll">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>
                    <b>{u.full_name || "—"}</b>
                  </td>
                  <td className="num" style={{ fontSize: 11.5 }}>
                    {u.email}
                  </td>
                  <td>
                    <select
                      className="inp"
                      style={{ width: "auto" }}
                      value={u.role}
                      disabled={u.id === currentUser?.id}
                      onChange={(e) => handleRoleChange(u, e.target.value)}
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {ROLE_LABEL[r]}
                        </option>
                      ))}
                    </select>
                    {u.id === currentUser?.id && <p className="hint">You cannot change your own role.</p>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="chead">
          <h2>Capability matrix</h2>
          <span className="scope">Click a cell to cycle: inherited → granted → revoked</span>
        </div>
        <div className="cbody">
          <CapabilityMatrix users={users} reference={reference} />
          <p className="hint" style={{ marginTop: 11 }}>
            <b>•</b>/<b>·</b> inherited from role (on/off) · <b>✓</b> explicitly granted · <b>✗</b> explicitly
            revoked. Controls that would lock you out of your own access are disabled.
          </p>
        </div>
      </div>
    </>
  );
}
