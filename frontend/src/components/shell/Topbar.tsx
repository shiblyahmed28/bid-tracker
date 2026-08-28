import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

import { api } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { BellIcon, MenuIcon, SyncIcon } from "../../icons";
import { formatSyncTime } from "../../lib/formatDate";
import { pageMetaFor } from "./navConfig";

interface TopbarProps {
  onOpenDrawer: () => void;
}

export function Topbar({ onOpenDrawer }: TopbarProps) {
  const { user } = useAuth();
  const location = useLocation();
  const { title, crumb } = pageMetaFor(location.pathname);

  const [lastSync, setLastSync] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  const isAdmin = user?.role === "admin";

  useEffect(() => {
    if (!isAdmin) return;
    api
      .get("/sync/runs/", { params: { page_size: 1 } })
      .then((response) => setLastSync(response.data.results?.[0]?.finished_at ?? null))
      .catch(() => {
        // Non-fatal — the indicator just stays blank until the next fetch.
      });
  }, [isAdmin]);

  async function handleFetchData() {
    setSyncing(true);
    try {
      const response = await api.post("/sync/run/");
      setLastSync(response.data.finished_at ?? null);
    } catch {
      // A failed manual sync isn't this component's to report in detail —
      // Sync history (admin) is where the real error surfaces.
    } finally {
      setSyncing(false);
    }
  }

  return (
    <header className="app-header">
      <button className="burger" onClick={onOpenDrawer} aria-label="Open menu">
        <MenuIcon />
      </button>
      <div>
        <h1>{title}</h1>
        {crumb && <div className="crumb">{crumb}</div>}
      </div>
      <div className="hgap" />

      <div className="sync-indicator">
        <span className="sync-dot" />
        {isAdmin && lastSync ? (
          <>
            Synced <b className="num">{formatSyncTime(lastSync)}</b>
          </>
        ) : (
          "Synced"
        )}
      </div>

      {isAdmin && (
        <button className="btn btn-s btn-sm" onClick={handleFetchData} disabled={syncing}>
          <SyncIcon style={{ width: 14, height: 14 }} />
          {syncing ? "Syncing…" : "Fetch data"}
        </button>
      )}

      <button className="bell" aria-label="Notifications">
        <BellIcon />
      </button>
    </header>
  );
}
