import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "./AuthContext";

export function ProtectedRoute() {
  const { user, isInitializing } = useAuth();
  const location = useLocation();

  if (isInitializing) {
    return <div className="auth-loading">Loading…</div>;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}
