import { useEffect, useState } from "react";

import { fetchUsers, type AdminUser } from "../api/accounts";
import {
  fetchDeadlineRules,
  fetchNotificationPolicies,
  fetchWelcomeEmailSettings,
  updateDeadlineRule,
  updateNotificationPolicy,
  updateWelcomeEmailSettings,
  type DeadlineReminderRuleItem,
  type NotificationPolicyItem,
  type WelcomeEmailSettingsData,
} from "../api/settings";
import { useToast } from "../components/ToastContext";
import { Skeleton } from "../dashboard/Skeleton";
import { formatFullDateTime } from "../lib/dateUtils";
import { RoleMultiSelect } from "./RoleMultiSelect";
import { UserMultiSelect } from "./UserMultiSelect";

// The dedicated deadline_reminder policy row is handled by its own section
// below (DeadlineReminderRule) — not shown a second time in this table.
const EXCLUDED_EVENT_KEYS = new Set(["deadline_reminder"]);

export function NotificationsSettingsTab() {
  const { showToast } = useToast();
  const [policies, setPolicies] = useState<NotificationPolicyItem[] | null>(null);
  const [rules, setRules] = useState<DeadlineReminderRuleItem[] | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [welcomeEmail, setWelcomeEmail] = useState<WelcomeEmailSettingsData | null>(null);

  useEffect(() => {
    fetchNotificationPolicies().then(setPolicies);
    fetchDeadlineRules().then(setRules);
    fetchUsers().then(setUsers);
    fetchWelcomeEmailSettings().then(setWelcomeEmail);
  }, []);

  async function handleWelcomeEmailToggle() {
    if (!welcomeEmail) return;
    try {
      const updated = await updateWelcomeEmailSettings(!welcomeEmail.enabled);
      setWelcomeEmail(updated);
      showToast(`Welcome emails turned ${updated.enabled ? "on" : "off"}`);
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? "Could not update that setting.");
    }
  }

  async function handlePolicyChange(policy: NotificationPolicyItem, patch: Partial<NotificationPolicyItem>) {
    try {
      const updated = await updateNotificationPolicy(policy.id, patch);
      setPolicies((prev) => (prev ? prev.map((p) => (p.id === policy.id ? updated : p)) : prev));
      showToast(`${policy.label} updated`);
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? "Could not update that policy.");
    }
  }

  async function handleRuleChange(rule: DeadlineReminderRuleItem, patch: Partial<DeadlineReminderRuleItem>) {
    try {
      const updated = await updateDeadlineRule(rule.id, patch);
      setRules((prev) => (prev ? prev.map((r) => (r.id === rule.id ? updated : r)) : prev));
      showToast(`${rule.days_before}-day reminder updated`);
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? "Could not update that reminder rule.");
    }
  }

  if (policies === null || rules === null) {
    return (
      <div className="card">
        <div className="cbody">
          <Skeleton height={260} />
        </div>
      </div>
    );
  }

  const visiblePolicies = policies.filter((p) => !EXCLUDED_EVENT_KEYS.has(p.event_key));

  return (
    <>
      <div className="card">
        <div className="chead">
          <h2>Event notifications</h2>
          <span className="scope">Admin-controlled defaults</span>
        </div>
        <div className="tscroll">
          <table>
            <thead>
              <tr>
                <th>Event</th>
                <th>In-app</th>
                <th>Email</th>
                <th>Applies to by default</th>
              </tr>
            </thead>
            <tbody>
              {visiblePolicies.map((policy) => (
                <tr key={policy.id}>
                  <td>
                    <b>{policy.label}</b>
                  </td>
                  <td>
                    <div
                      className={`toggle${policy.default_in_app ? " on" : ""}`}
                      onClick={() => handlePolicyChange(policy, { default_in_app: !policy.default_in_app })}
                    />
                  </td>
                  <td>
                    <div
                      className={`toggle${policy.default_email ? " on" : ""}`}
                      onClick={() => handlePolicyChange(policy, { default_email: !policy.default_email })}
                    />
                  </td>
                  <td>
                    <RoleMultiSelect
                      value={policy.applies_to_roles}
                      onChange={(roles) => handlePolicyChange(policy, { applies_to_roles: roles })}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="cbody">
          <p className="hint">
            Users can override these defaults for their own notifications from their own settings.
          </p>
        </div>
      </div>

      <div className="card">
        <div className="chead">
          <h2>Deadline reminders</h2>
          <span className="scope">Sent 7, 14 or 21 days before submission</span>
        </div>
        <div className="cbody">
          {rules.map((rule) => (
            <div className="form-section" key={rule.id}>
              <h3 style={{ display: "flex", alignItems: "center", gap: 10 }}>
                {rule.days_before}-day reminder
                <div
                  className={`toggle${rule.is_active ? " on" : ""}`}
                  onClick={() => handleRuleChange(rule, { is_active: !rule.is_active })}
                />
                <span className="hint" style={{ fontWeight: 400, textTransform: "none" }}>
                  {rule.is_active ? "Active" : "Inactive"}
                </span>
              </h3>
              <div className="frow">
                <div className="field">
                  <label>Applies to roles</label>
                  <RoleMultiSelect
                    value={rule.applies_to_roles}
                    onChange={(roles) => handleRuleChange(rule, { applies_to_roles: roles })}
                  />
                </div>
                <div className="field">
                  <label>Also notify specific users</label>
                  <UserMultiSelect
                    users={users}
                    selectedIds={rule.users}
                    onChange={(ids) => handleRuleChange(rule, { users: ids })}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="chead">
          <h2>Welcome emails</h2>
          <span className="scope">Engaged resources · §Phase 20</span>
        </div>
        <div className="cbody">
          {welcomeEmail === null ? (
            <Skeleton height={60} />
          ) : (
            <>
              <h3 style={{ display: "flex", alignItems: "center", gap: 10 }}>
                Send welcome emails
                <div className={`toggle${welcomeEmail.enabled ? " on" : ""}`} onClick={handleWelcomeEmailToggle} />
                <span className="hint" style={{ fontWeight: 400, textTransform: "none" }}>
                  {welcomeEmail.enabled ? "On" : "Off"}
                </span>
              </h3>
              <p className="hint" style={{ textTransform: "none", fontSize: 12.5, marginTop: 4 }}>
                Default off — nothing sends until this is turned on. Individual sends still need an admin to
                click Send on the Engaged Resources screen; this only unlocks that button.
                {welcomeEmail.updated_by_email && (
                  <> Last changed by {welcomeEmail.updated_by_email} ({formatFullDateTime(welcomeEmail.updated_at)}).</>
                )}
              </p>
              <div className="banner b-warn" style={{ marginTop: 10 }}>
                Run the duplicate-merge tool on Engaged Resources before turning this on — a duplicate record
                could otherwise miss its welcome email entirely.
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
