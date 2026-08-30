import { useEffect, useState } from "react";

import { fetchSheetAppendSettings, updateSheetAppendSettings, type SheetAppendSettingsData } from "../api/settings";
import { useToast } from "../components/ToastContext";
import { Skeleton } from "../dashboard/Skeleton";
import { formatFullDateTime } from "../lib/dateUtils";

export function SyncSettingsTab() {
  const { showToast } = useToast();
  const [settings, setSettings] = useState<SheetAppendSettingsData | null>(null);

  useEffect(() => {
    fetchSheetAppendSettings().then(setSettings);
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

  return (
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
  );
}
