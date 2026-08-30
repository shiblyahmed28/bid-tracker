import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  adminResetPassword,
  createUser,
  fetchUsers,
  updateUser,
  type AdminUser,
} from "../../api/accounts";
import { useAuth } from "../../auth/AuthContext";
import type { Role } from "../../auth/AuthContext";
import { Modal } from "../../components/Modal";
import { useToast } from "../../components/ToastContext";
import { ToggleRow } from "../../components/ToggleRow";
import { Skeleton } from "../../dashboard/Skeleton";
import { passwordStrength } from "../../lib/passwordStrength";

const ROLE_LABEL: Record<string, string> = { admin: "Admin", editor: "Editor", viewer: "Viewer" };
const ROLE_TAG: Record<string, string> = { admin: "t-won", editor: "t-sub", viewer: "t-no" };
const ROLES: Role[] = ["viewer", "editor", "admin"];

// Mirrors the server's actual rule (ALLOWED_EMAIL_DOMAIN) closely enough for
// UX purposes only — the server is still the real gate (§Phase 21 item 1).
const COMPANY_EMAIL_RE = /^[^@\s]+@spectrum-bd\.com$/i;
function isExternalEmail(email: string): boolean {
  return email.trim() !== "" && !COMPANY_EMAIL_RE.test(email.trim());
}

function fieldErrors(data: unknown): string[] {
  if (!data || typeof data !== "object") return ["Something went wrong. Please try again."];
  const messages: string[] = [];
  for (const [field, value] of Object.entries(data as Record<string, unknown>)) {
    const text = Array.isArray(value) ? value.join(" ") : String(value);
    messages.push(field === "non_field_errors" ? text : `${field}: ${text}`);
  }
  return messages.length ? messages : ["Something went wrong. Please try again."];
}

function ResetPasswordModal({ user, onClose }: { user: AdminUser; onClose: () => void }) {
  const { showToast } = useToast();
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [forceChange, setForceChange] = useState(true);
  const [emailUser, setEmailUser] = useState(true);
  const [revokeSessions, setRevokeSessions] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const strength = passwordStrength(newPassword);

  async function handleSubmit() {
    setSaving(true);
    setErrors([]);
    try {
      const result = await adminResetPassword(user.id, {
        new_password: newPassword,
        confirm_password: confirm,
        force_change: forceChange,
        email_user: emailUser,
        revoke_sessions: revokeSessions,
      });
      showToast(`Password reset for ${user.full_name || user.email}${result.emailed ? " — user emailed" : ""}`);
      onClose();
    } catch (err: any) {
      setErrors(fieldErrors(err?.response?.data));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Reset password — ${user.full_name || user.email}`}
      footer={
        <>
          <button className="btn btn-s" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button className="btn btn-p" onClick={handleSubmit} disabled={saving || !newPassword || !confirm}>
            {saving ? "Resetting…" : "Reset password"}
          </button>
        </>
      }
    >
      <div className="field">
        <label className="req">New password</label>
        <input
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          placeholder="At least 10 characters"
        />
        <div className="pwbar">
          <i style={{ width: `${strength.percent}%`, background: strength.color }} />
        </div>
      </div>
      <div className="field">
        <label className="req">Confirm</label>
        <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
      </div>

      <ToggleRow
        label="Force change at next sign-in"
        hint="User must set their own password before continuing"
        checked={forceChange}
        onChange={setForceChange}
      />
      <ToggleRow
        label="Email the user"
        hint="Sends a notice that an admin reset their password"
        checked={emailUser}
        onChange={setEmailUser}
      />
      <ToggleRow
        label="End all their sessions"
        hint="Signs them out everywhere immediately"
        checked={revokeSessions}
        onChange={setRevokeSessions}
      />

      {errors.map((e) => (
        <p className="err" key={e}>
          {e}
        </p>
      ))}

      <div className="banner b-warn" style={{ marginTop: 14 }}>
        This is written to the audit log as a password reset by you, with a timestamp. The old password is
        never visible to anyone, including admins.
      </div>
    </Modal>
  );
}

function AddUserModal({ onClose, onCreated }: { onClose: () => void; onCreated: (user: AdminUser) => void }) {
  const { showToast } = useToast();
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [password, setPassword] = useState("");
  const [forceChange, setForceChange] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const strength = passwordStrength(password);
  const isExternal = isExternalEmail(email);

  async function handleSubmit() {
    setSaving(true);
    setErrors([]);
    try {
      const user = await createUser({
        full_name: fullName,
        phone,
        email,
        role: isExternal ? "viewer" : role,
        password,
        must_change_password: forceChange,
      });
      showToast(`${user.full_name || user.email} added`);
      onCreated(user);
    } catch (err: any) {
      setErrors(fieldErrors(err?.response?.data));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Add user"
      footer={
        <>
          <button className="btn btn-s" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button
            className="btn btn-p"
            onClick={handleSubmit}
            disabled={saving || !fullName || !email || !password}
          >
            {saving ? "Creating…" : "Create user"}
          </button>
        </>
      }
    >
      <div className="frow">
        <div className="field">
          <label className="req">Full name</label>
          <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Full name" />
        </div>
        <div className="field">
          <label>Phone</label>
          <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+880 1XXXXXXXXX" />
        </div>
      </div>
      <div className="field">
        <label className="req">Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@spectrum-bd.com" />
        <p className="hint">
          Company domain (<b>@spectrum-bd.com</b>) or any other domain for an external account — external
          accounts are always viewers and can't be promoted.
        </p>
      </div>
      <div className="frow">
        <div className="field">
          <label className="req">Role</label>
          <select value={isExternal ? "viewer" : role} disabled={isExternal} onChange={(e) => setRole(e.target.value as Role)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABEL[r]}
              </option>
            ))}
          </select>
          {isExternal && <p className="hint">External-domain accounts are always viewers.</p>}
        </div>
        <div className="field">
          <label className="req">Temporary password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <div className="pwbar">
            <i style={{ width: `${strength.percent}%`, background: strength.color }} />
          </div>
        </div>
      </div>
      <ToggleRow
        label="Force change at first sign-in"
        hint="Recommended"
        checked={forceChange}
        onChange={setForceChange}
      />
      {errors.map((e) => (
        <p className="err" key={e}>
          {e}
        </p>
      ))}
    </Modal>
  );
}

function EditUserModal({
  user,
  isSelf,
  onClose,
  onUpdated,
}: {
  user: AdminUser;
  isSelf: boolean;
  onClose: () => void;
  onUpdated: (user: AdminUser) => void;
}) {
  const { showToast } = useToast();
  const [fullName, setFullName] = useState(user.full_name);
  const [phone, setPhone] = useState(user.phone);
  const [email, setEmail] = useState(user.email);
  const [role, setRole] = useState<Role>(user.role);
  const [isActive, setIsActive] = useState(user.is_active);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const isExternal = isExternalEmail(email);

  async function handleSubmit() {
    setSaving(true);
    setErrors([]);
    try {
      const updated = await updateUser(user.id, {
        full_name: fullName,
        phone,
        email,
        role: isExternal ? "viewer" : role,
        is_active: isActive,
      });
      showToast(`${updated.full_name || updated.email} updated`);
      onUpdated(updated);
    } catch (err: any) {
      setErrors(fieldErrors(err?.response?.data));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Edit user — ${user.full_name || user.email}`}
      footer={
        <>
          <button className="btn btn-s" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button className="btn btn-p" onClick={handleSubmit} disabled={saving || !fullName || !email}>
            {saving ? "Saving…" : "Save changes"}
          </button>
        </>
      }
    >
      <div className="frow">
        <div className="field">
          <label className="req">Full name</label>
          <input value={fullName} onChange={(e) => setFullName(e.target.value)} />
        </div>
        <div className="field">
          <label>Phone</label>
          <input value={phone} onChange={(e) => setPhone(e.target.value)} />
        </div>
      </div>
      <div className="field">
        <label className="req">Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} />
        <p className="hint">
          Company domain (<b>@spectrum-bd.com</b>) or any other domain for an external account — external
          accounts are always viewers and can't be promoted.
        </p>
      </div>
      <div className="frow">
        <div className="field">
          <label>Role</label>
          <select
            value={isExternal ? "viewer" : role}
            disabled={isSelf || isExternal}
            onChange={(e) => setRole(e.target.value as Role)}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABEL[r]}
              </option>
            ))}
          </select>
          {isSelf && <p className="hint">You cannot change your own role.</p>}
          {!isSelf && isExternal && <p className="hint">External-domain accounts are always viewers.</p>}
        </div>
        <div className="field">
          <label>Status</label>
          <select value={isActive ? "active" : "suspended"} onChange={(e) => setIsActive(e.target.value === "active")}>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
          </select>
        </div>
      </div>
      {errors.map((e) => (
        <p className="err" key={e}>
          {e}
        </p>
      ))}
    </Modal>
  );
}

export function UsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [resetTarget, setResetTarget] = useState<AdminUser | null>(null);
  const [editTarget, setEditTarget] = useState<AdminUser | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  useEffect(() => {
    fetchUsers().then(setUsers);
  }, []);

  function upsert(user: AdminUser) {
    setUsers((prev) => {
      if (!prev) return prev;
      const exists = prev.some((u) => u.id === user.id);
      return exists ? prev.map((u) => (u.id === user.id ? user : u)) : [...prev, user];
    });
  }

  if (users === null) {
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
      <div style={{ display: "flex", marginBottom: 13 }}>
        <div className="hgap" />
        <button className="btn btn-p" onClick={() => setShowAdd(true)}>
          Add user
        </button>
      </div>

      <div className="card">
        <div className="chead">
          <h2>Accounts</h2>
          <span className="scope">Admin only</span>
        </div>
        <div className="tscroll">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Phone</th>
                <th>Status</th>
                <th></th>
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
                    {u.is_external && (
                      <span className="tag t-pend" style={{ marginLeft: 6 }} title="Not on the company domain">
                        External
                      </span>
                    )}
                  </td>
                  <td>
                    <span className={`tag ${ROLE_TAG[u.role]}`}>{ROLE_LABEL[u.role]}</span>
                  </td>
                  <td className="num" style={{ fontSize: 11.5 }}>
                    {u.phone || "—"}
                  </td>
                  <td>
                    <span className={`tag ${u.is_active ? "t-won" : "t-lost"}`}>
                      {u.is_active ? "Active" : "Suspended"}
                    </span>
                  </td>
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    <Link className="btn btn-s btn-sm" to={`/sessions?user=${u.id}`}>
                      Sessions
                    </Link>{" "}
                    <button className="btn btn-s btn-sm" onClick={() => setEditTarget(u)}>
                      Edit
                    </button>{" "}
                    <button className="btn btn-s btn-sm" onClick={() => setResetTarget(u)}>
                      Reset password
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="chead">
          <h2>What each role can do</h2>
        </div>
        <div className="cbody">
          <div className="trow">
            <div className="tn">
              <b>Viewer</b>
              <small>
                Both dashboards, all bids, details, PDF export. Own profile and own sign-in history. Receives
                notifications. Cannot create, edit or delete.
              </small>
            </div>
          </div>
          <div className="trow">
            <div className="tn">
              <b>Editor</b>
              <small>
                Everything a viewer can do, plus create bids, edit records and resolve sync conflicts. No user
                management, no sync history, no audit log.
              </small>
            </div>
          </div>
          <div className="trow">
            <div className="tn">
              <b>Admin</b>
              <small>
                Everything, plus user management, password resets, every user's sign-in history, sync history
                and the full audit log.
              </small>
            </div>
          </div>
        </div>
      </div>

      {resetTarget && <ResetPasswordModal user={resetTarget} onClose={() => setResetTarget(null)} />}
      {editTarget && (
        <EditUserModal
          user={editTarget}
          isSelf={editTarget.id === currentUser?.id}
          onClose={() => setEditTarget(null)}
          onUpdated={(u) => {
            upsert(u);
            setEditTarget(null);
          }}
        />
      )}
      {showAdd && (
        <AddUserModal
          onClose={() => setShowAdd(false)}
          onCreated={(u) => {
            upsert(u);
            setShowAdd(false);
          }}
        />
      )}
    </>
  );
}
