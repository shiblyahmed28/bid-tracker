import { useEffect, useState } from "react";

import {
  fetchEmailServiceSettings,
  fetchSheetAppendSettings,
  fetchSyncScheduleSettings,
  updateEmailServiceSettings,
  updateSheetAppendSettings,
  updateSyncScheduleSettings,
  type EmailServiceSettingsData,
  type SheetAppendSettingsData,
  type SyncScheduleSettingsData,
} from "../api/settings";
import { resetBidData } from "../api/sync";
import { Modal } from "../components/Modal";
import { useToast } from "../components/ToastContext";
import { Skeleton } from "../dashboard/Skeleton";
import { formatFullDateTime } from "../lib/dateUtils";

const CONFIRM_PHRASE = "RESET";

export function SyncSettingsTab() {
  const { showToast } = useToast();
  const [settings, setSettings] = useState<SheetAppendSettingsData | null>(null);
  const [schedule, setSchedule] = useState<SyncScheduleSettingsData | null>(null);
  const [intervalInput, setIntervalInput] = useState("");
  const [savingInterval, setSavingInterval] = useState(false);
  const [emailService, setEmailService] = useState<EmailServiceSettingsData | null>(null);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    fetchSheetAppendSettings().then(setSettings);
    fetchSyncScheduleSettings().then((data) => {
      setSchedule(data);
      setIntervalInput(String(data.interval_hours));
    });
    fetchEmailServiceSettings().then(setEmailService);
  }, []);

  async function handleToggle() {
    if (!settings) return;
    try {
      const updated = await updateSheetAppendSettings(!settings.enabled);
      setSettings(updated);
      showToast(`Sheet append turned ${updated.enabled ? "on" : "off"}`);
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? "Could not update that setting.");
    }
  }

  async function handleSaveInterval() {
    const hours = Number(intervalInput);
    if (!Number.isInteger(hours) || hours < 1 || hours > 168) {
      showToast("Enter a whole number of hours between 1 and 168.");
      return;
    }
    setSavingInterval(true);
    try {
      const updated = await updateSyncScheduleSettings(hours);
      setSchedule(updated);
      setIntervalInput(String(updated.interval_hours));
      showToast(`Automatic sync now runs every ${updated.interval_hours}h`);
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? "Could not update the sync schedule.");
    } finally {
      setSavingInterval(false);
    }
  }

  async function handleToggleEmailService() {
    if (!emailService) return;
    try {
      const updated = await updateEmailServiceSettings(!emailService.enabled);
      setEmailService(updated);
      showToast(`Email service turned ${updated.enabled ? "on" : "off"}`);
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? "Could not update that setting.");
    }
  }

  function closeResetModal() {
    setShowResetConfirm(false);
    setConfirmText("");
  }

  async function handleReset() {
    setResetting(true);
    try {
      const result = await resetBidData();
      showToast(
        `Reset complete — deleted ${result.deleted}, resynced ${result.sync_run.rows_created} created` +
          (result.sync_run.rows_quarantined ? `, ${result.sync_run.rows_quarantined} quarantined` : "")
      );
      closeResetModal();
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? "Could not reset bid data.");
    } finally {
      setResetting(false);
    }
  }

  return (
    <>
      <div className="card">
        <div className="chead">
          <h2>Sheet append-back</h2>
          <span className="scope">§Phase 23</span>
        </div>
        <div className="cbody">
          {settings === null ? (
            <Skeleton height={60} />
          ) : (
            <>
              <h3 style={{ display: "flex", alignItems: "center", gap: 10 }}>
                Append new bids to the sheet
                <div className={`toggle${settings.enabled ? " on" : ""}`} onClick={handleToggle} />
                <span className="hint" style={{ fontWeight: 400, textTransform: "none" }}>
                  {settings.enabled ? "On" : "Off"}
                </span>
              </h3>
              <p className="hint" style={{ textTransform: "none", fontSize: 12.5, marginTop: 4 }}>
                Default off. When a bid is created in the app while this is on, one row is appended to the
                live Google Sheet with that bid's uid and every sheet-mapped field — team, engaged
                resources, engagement dates and cost lines have no sheet column and are never written.
                After appending, the bid syncs like any other sheet row. Existing rows are never updated or
                deleted; the only in-place write remains the uid backfill.
                {settings.updated_by_email && (
                  <> Last changed by {settings.updated_by_email} ({formatFullDateTime(settings.updated_at)}).</>
                )}
              </p>
              <div className="banner b-warn" style={{ marginTop: 10 }}>
                This modifies the live production spreadsheet. Turning it on means every future bid created
                here writes a new row to that sheet — make sure the team is ready for that before enabling it.
              </div>
            </>
          )}
        </div>
      </div>

      <div className="card">
        <div className="chead">
          <h2>Sync schedule</h2>
          <span className="scope">Automatic sync interval</span>
        </div>
        <div className="cbody">
          {schedule === null ? (
            <Skeleton height={60} />
          ) : (
            <>
              <h3 style={{ fontWeight: 400, textTransform: "none" }}>
                Run the automatic sync every
                <input
                  type="number"
                  className="inp"
                  min={1}
                  max={168}
                  value={intervalInput}
                  onChange={(e) => setIntervalInput(e.target.value)}
                  style={{ width: 70, margin: "0 8px" }}
                />
                hours
                <button
                  className="btn btn-s btn-sm"
                  style={{ marginLeft: 10 }}
                  onClick={handleSaveInterval}
                  disabled={savingInterval || Number(intervalInput) === schedule.interval_hours}
                >
                  {savingInterval ? "Saving…" : "Save"}
                </button>
              </h3>
              <p className="hint" style={{ textTransform: "none", fontSize: 12.5, marginTop: 4 }}>
                Default 8 hours (the original fixed 00:00 / 08:00 / 16:00 Dhaka schedule). A change here
                takes effect on the next check — the schedule is checked every 15 minutes, but only
                actually syncs once this many hours have passed since the last automatic run. Manual
                "Fetch data" is never affected by this setting.
                {schedule.updated_by_email && (
                  <> Last changed by {schedule.updated_by_email} ({formatFullDateTime(schedule.updated_at)}).</>
                )}
              </p>
            </>
          )}
        </div>
      </div>

      <div className="card">
        <div className="chead">
          <h2>Email service</h2>
          <span className="scope">Global kill switch</span>
        </div>
        <div className="cbody">
          {emailService === null ? (
            <Skeleton height={60} />
          ) : (
            <>
              <h3 style={{ display: "flex", alignItems: "center", gap: 10 }}>
                Send outbound email
                <div
                  className={`toggle${emailService.enabled ? " on" : ""}`}
                  onClick={handleToggleEmailService}
                />
                <span className="hint" style={{ fontWeight: 400, textTransform: "none" }}>
                  {emailService.enabled ? "On" : "Off"}
                </span>
              </h3>
              <p className="hint" style={{ textTransform: "none", fontSize: 12.5, marginTop: 4 }}>
                Default on. Turning this off blocks every outbound email the app sends — new-bid alerts,
                change digests, deadline reminders, welcome emails and admin password resets — regardless
                of any other setting. In-app notifications (the bell) are not affected. Every blocked
                attempt is still recorded in the Email log, marked failed with the reason.
                {emailService.updated_by_email && (
                  <> Last changed by {emailService.updated_by_email} ({formatFullDateTime(emailService.updated_at)}).</>
                )}
              </p>
              {!emailService.enabled && (
                <div className="banner b-warn" style={{ marginTop: 10 }}>
                  Email is currently off system-wide. No one will receive new-bid alerts, deadline
                  reminders, digests, welcome emails, or password-reset emails until this is turned back on.
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <div className="card">
        <div className="chead">
          <h2>Danger zone</h2>
          <span className="scope">Admin only</span>
        </div>
        <div className="cbody">
          <h3 style={{ fontWeight: 400, textTransform: "none" }}>Reset all bid data</h3>
          <p className="hint" style={{ textTransform: "none", fontSize: 12.5, marginTop: 4 }}>
            Permanently deletes every bid — sheet-synced and app-created alike, along with their
            engagements and cost lines — then immediately re-syncs fresh from the sheet. Use this when
            switching to a different sheet, or to clear out mismatched data and rebuild cleanly. No
            notifications are sent for the rebuild, since every row is "new" again by definition. Client,
            engaged-resource and team reference records are not touched. This cannot be undone.
          </p>
          <button className="btn btn-d" style={{ marginTop: 10 }} onClick={() => setShowResetConfirm(true)}>
            Reset all bid data…
          </button>
        </div>
      </div>

      <Modal
        open={showResetConfirm}
        onClose={closeResetModal}
        title="Reset all bid data"
        footer={
          <>
            <button className="btn btn-s" onClick={closeResetModal} disabled={resetting}>
              Cancel
            </button>
            <button
              className="btn btn-d"
              onClick={handleReset}
              disabled={resetting || confirmText !== CONFIRM_PHRASE}
            >
              {resetting ? "Resetting…" : "Delete everything and resync"}
            </button>
          </>
        }
      >
        <p>
          This deletes <strong>every bid record</strong> in the database — sheet-synced and app-created —
          and everything attached to them (engagements, cost lines), then re-syncs fresh from the sheet.
          There is no undo.
        </p>
        <p className="hint" style={{ textTransform: "none", fontSize: 12.5, marginTop: 10 }}>
          Type <strong>{CONFIRM_PHRASE}</strong> to confirm.
        </p>
        <input
          type="text"
          className="inp"
          value={confirmText}
          onChange={(e) => setConfirmText(e.target.value)}
          placeholder={CONFIRM_PHRASE}
          style={{ marginTop: 6, width: "100%" }}
          autoFocus
        />
      </Modal>
    </>
  );
}
