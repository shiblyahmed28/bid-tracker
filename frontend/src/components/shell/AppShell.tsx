import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { ErrorBoundary } from "../ErrorBoundary";
import { useEscapeKey } from "../../lib/useEscapeKey";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();

  // Covers browser back/forward too, not just Sidebar's own link clicks.
  useEffect(() => setDrawerOpen(false), [location.pathname]);

  useEscapeKey(() => setDrawerOpen(false), drawerOpen);

  return (
    <>
      <div className={`scrim${drawerOpen ? " on" : ""}`} onClick={() => setDrawerOpen(false)} />
      <Sidebar open={drawerOpen} onNavigate={() => setDrawerOpen(false)} />
      <div className="app-main">
        <Topbar onOpenDrawer={() => setDrawerOpen(true)} />
        <div className="wrap">
          <ErrorBoundary key={location.pathname}>
            <Outlet />
          </ErrorBoundary>
        </div>
      </div>
    </>
  );
}
