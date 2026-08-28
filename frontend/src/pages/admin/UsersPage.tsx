import { useEffect, useState } from "react";

import { adminResetPassword, fetchUsers, type AdminUser } from "../../api/accounts";
import { Modal } from "../../components/Modal";
import { useToast } from "../../components/ToastContext";
import { ToggleRow } from "../../components/ToggleRow";
import { Skeleton } from "../../dashboard/Skeleton";
import { passwordStrength } from "../../lib/passwordStrength";

const ROLE_LABEL: Record<string, string> = { admin: "Admin", editor: "Editor", viewer: "Viewer" };
const ROLE_TAG: Record<string, string> = { admin: "t-won", editor: "t-sub", viewer: "t-no" };

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

export function UsersPage() {
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [resetTarget, setResetTarget] = useState<AdminUser | null>(null);

  useEffect(() => {
    fetchUsers().then(setUsers);
  }, []);

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
        <div className="cbody">
          <p className="hint">
            Adding users, editing details and changing roles arrive in a later phase — this page currently
            covers admin-triggered password resets only.
          </p>
        </div>
      </div>

      {resetTarget && <ResetPasswordModal user={resetTarget} onClose={() => setResetTarget(null)} />}
    </>
  );
}
