import { useState } from "react";

import { resolveConflict, type ConflictSummary } from "../api/bids";

interface ConflictBannerProps {
  conflicts: ConflictSummary[];
  onResolved: () => void;
}

/** "Sheet says X, you set Y" with Keep mine / Take sheet's (§9). Editors and
 * admins only — the caller gates who ever renders this. */
export function ConflictBanner({ conflicts, onResolved }: ConflictBannerProps) {
  const [resolvingId, setResolvingId] = useState<number | null>(null);

  if (!conflicts.length) return null;

  async function handleResolve(id: number, choose: "sheet" | "local") {
    setResolvingId(id);
    try {
      await resolveConflict(id, choose);
      onResolved();
    } finally {
      setResolvingId(null);
    }
  }

  return (
    <div className="banner b-warn" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {conflicts.map((conflict) => (
        <div key={conflict.id}>
          <div>
            <strong>{conflict.field}</strong> — Sheet says <b>{conflict.sheet_value || "—"}</b>, you set{" "}
            <b>{conflict.local_value || "—"}</b>
            {conflict.local_editor && <span> ({conflict.local_editor})</span>}
          </div>
          <div style={{ marginTop: 6, display: "flex", gap: 8 }}>
            <button
              className="btn btn-s btn-sm"
              disabled={resolvingId === conflict.id}
              onClick={() => handleResolve(conflict.id, "local")}
            >
              Keep mine
            </button>
            <button
              className="btn btn-p btn-sm"
              disabled={resolvingId === conflict.id}
              onClick={() => handleResolve(conflict.id, "sheet")}
            >
              Take sheet's
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
