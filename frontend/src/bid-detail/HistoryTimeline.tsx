import { useEffect, useState } from "react";

import { fetchBidHistory, type HistoryEntry } from "../api/bids";
import { Skeleton } from "../dashboard/Skeleton";
import { formatSyncTime } from "../lib/formatDate";

const ACTION_LABELS: Record<string, string> = {
  bid_create: "Created",
  bid_update: "Updated",
  bid_soft_delete: "Deleted",
  bid_restore: "Restored",
  conflict_resolution: "Conflict resolved",
};

/** The bid's change history as a timeline (§11) — who made each change and
 * whether it was manual or a sync, per §15. */
export function HistoryTimeline({ bidId }: { bidId: string }) {
  const [entries, setEntries] = useState<HistoryEntry[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchBidHistory(bidId).then((response) => {
      if (!cancelled) setEntries(response.results);
    });
    return () => {
      cancelled = true;
    };
  }, [bidId]);

  if (entries === null) return <Skeleton height={200} />;
  if (!entries.length) return <p className="hint">No changes recorded yet.</p>;

  return (
    <ul className="tl">
      {entries.map((entry) => {
        const who = entry.actor_email ?? entry.actor_label ?? "System (sync)";
        const isManual = entry.actor !== null;
        const label = ACTION_LABELS[entry.action] ?? entry.action;

        return (
          <li key={entry.id}>
            <div>
              <strong>{label}</strong>
              {entry.field && ` · ${entry.field}`} <span className="mini">{isManual ? "Manual" : "Sync"}</span>
            </div>
            {entry.field && (entry.old_value || entry.new_value) && (
              <div className="hint">
                {entry.old_value || "—"} → {entry.new_value || "—"}
              </div>
            )}
            <div className="hint">by {who}</div>
            <time>{formatSyncTime(entry.created_at)}</time>
          </li>
        );
      })}
    </ul>
  );
}
