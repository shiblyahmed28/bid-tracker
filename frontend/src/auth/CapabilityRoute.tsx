import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "./AuthContext";

/** Gates a route by a named capability rather than a role (§Phase 16) — an
 * admin can grant `access_master_settings` to a specific editor or viewer,
 * so this can't be a <RoleRoute>. */
export function CapabilityRoute({ requires }: { requires: string }) {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!user.capabilities.includes(requires)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
