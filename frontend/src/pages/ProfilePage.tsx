import { useState } from "react";

import { changePassword, updateProfile } from "../api/accounts";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/ToastContext";
import { formatDMY } from "../lib/dateUtils";
import { initials } from "../lib/initials";
import { passwordStrength } from "../lib/passwordStrength";

const COMPANY_EMAIL_RE = /^[^@\s]+@spectrum-bd\.com$/i;

function fieldErrors(data: unknown): string[] {
  if (!data || typeof data !== "object") return ["Something went wrong. Please try again."];
  const messages: string[] = [];
  for (const [field, value] of Object.entries(data as Record<string, unknown>)) {
    const text = Array.isArray(value) ? value.join(" ") : String(value);
    messages.push(field === "non_field_errors" ? text : `${field}: ${text}`);
  }
  return messages.length ? messages : ["Something went wrong. Please try again."];
}

const ROLE_LABEL: Record<string, string> = { admin: "Admin", editor: "Editor", viewer: "Viewer" };
const ROLE_TAG: Record<string, string> = { admin: "t-won", editor: "t-sub", viewer: "t-no" };

function ProfileCard() {
  const { user, refreshUser } = useAuth();
  const { showToast } = useToast();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  if (!user) return null;

  const emailInvalid = email.trim() !== "" && !COMPANY_EMAIL_RE.test(email.trim());

  async function handleSave() {
    if (emailInvalid) return;
    setSaving(true);
    setErrors([]);
    try {
      await updateProfile({ full_name: fullName, phone, email });
      await refreshUser();
      showToast("Profile saved");
    } catch (err: any) {
      setErrors(fieldErrors(err?.response?.data));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card">
      <div className="chead">
        <h2>Profile</h2>
        <span className="scope">Your details</span>
      </div>
      <div className="cbody">
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 18 }}>
          <div className="av" style={{ width: 56, height: 56, fontSize: 19, flex: "0 0 56px" }}>
            {initials(user.full_name, user.email)}
          </div>
          <div>
            <b style={{ fontSize: 16 }}>{user.full_name || user.email}</b>
            <div style={{ marginTop: 5 }}>
              <span className={`tag ${ROLE_TAG[user.role]}`}>{ROLE_LABEL[user.role]}</span>
            </div>
          </div>
        </div>

        <div className="frow">
          <div className="field">
            <label className="req">Full name</label>
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </div>
          <div className="field">
            <label>Phone number</label>
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+880 1XXXXXXXXX"
            />
          </div>
        </div>

        <div className="field">
          <label className="req">Email</label>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={emailInvalid ? { borderColor: "var(--danger)" } : undefined}
          />
          {emailInvalid && (
            <p className="err">
              Only <b>@spectrum-bd.com</b> addresses are allowed.
            </p>
          )}
          <p className="hint">Company domain only. Changing this changes your sign-in address.</p>
        </div>

        <div className="frow">
          <div className="field">
            <label>Role</label>
            <input value={ROLE_LABEL[user.role]} disabled style={{ background: "#F2F5F0", color: "var(--muted)" }} />
            <p className="hint">Only an admin can change your role.</p>
          </div>
          <div className="field">
            <label>Member since</label>
            <input
              value={formatDMY(user.date_joined.slice(0, 10))}
              disabled
              style={{ background: "#F2F5F0", color: "var(--muted)" }}
            />
          </div>
        </div>

        {errors.map((e) => (
          <p className="err" key={e}>
            {e}
          </p>
        ))}

        <button className="btn btn-p" onClick={handleSave} disabled={saving || emailInvalid}>
          {saving ? "Saving…" : "Save changes"}
        </button>
      </div>
    </div>
  );
}

function ChangePasswordCard() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const strength = passwordStrength(next);

  async function handleSubmit() {
    setSaving(true);
    setErrors([]);
    try {
      const result = await changePassword({
        current_password: current,
        new_password: next,
        confirm_password: confirm,
      });
      setCurrent("");
      setNext("");
      setConfirm("");
      showToast(
        result.revoked_sessions > 0
          ? `Password updated — signed out ${result.revoked_sessions} other session(s)`
          : "Password updated"
      );
    } catch (err: any) {
      setErrors(fieldErrors(err?.response?.data));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card">
      <div className="chead">
        <h2>Change password</h2>
        <span className="scope">Security</span>
      </div>
      <div className="cbody">
        <div className="field">
          <label className="req">Current password</label>
          <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} placeholder="••••••••" />
        </div>
        <div className="field">
          <label className="req">New password</label>
          <input
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            placeholder="At least 10 characters"
          />
          <div className="pwbar">
            <i style={{ width: `${strength.percent}%`, background: strength.color }} />
          </div>
          <p className="hint">{strength.message}</p>
        </div>
        <div className="field">
          <label className="req">Confirm new password</label>
          <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Repeat it" />
        </div>

        {errors.map((e) => (
          <p className="err" key={e}>
            {e}
          </p>
        ))}

        <button
          className="btn btn-p"
          onClick={handleSubmit}
          disabled={saving || !current || !next || !confirm}
        >
          {saving ? "Updating…" : "Update password"}
        </button>

        <div className="banner b-info" style={{ margin: "16px 0 0" }}>
          Changing your password signs you out of every other device. You will stay signed in here.
        </div>
        {user?.role === "admin" && (
          <div className="banner b-warn" style={{ marginTop: 11 }}>
            <b>Admin.</b> You can reset any user's password from <b>Users</b> → Reset password. The user can be
            emailed and forced to change it at next sign-in.
          </div>
        )}
      </div>
    </div>
  );
}

export function ProfilePage() {
  return (
    <div className="grid c2">
      <ProfileCard />
      <ChangePasswordCard />
    </div>
  );
}
