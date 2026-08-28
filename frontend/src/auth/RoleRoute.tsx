import { Navigate, Outlet } from "react-router-dom";

import { type Role, useAuth } from "./AuthContext";

const ROLE_RANK: Record<Role, number> = { viewer: 0, editor: 1, admin: 2 };

/** Gates a nested route tree to `requires` and every role above it (§11) —
 * used inside a <ProtectedRoute> subtree, so `user` is normally already set;
 * still falls back to /login defensively if it somehow isn't. */
export function RoleRoute({ requires }: { requires: Role }) {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (ROLE_RANK[user.role] < ROLE_RANK[requires]) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
