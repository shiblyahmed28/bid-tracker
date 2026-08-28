import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { RoleRoute } from "./auth/RoleRoute";
import { AppShell } from "./components/shell/AppShell";
import { ToastProvider } from "./components/ToastContext";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ClassicPage } from "./pages/ClassicPage";
import { BidsPage } from "./pages/BidsPage";
import { CreateBidPage } from "./pages/CreateBidPage";
import { BidDetailPage } from "./pages/BidDetailPage";
import { ProfilePage } from "./pages/ProfilePage";
import { SessionsPage } from "./pages/SessionsPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { SyncHistoryPage } from "./pages/admin/SyncHistoryPage";
import { AuditLogPage } from "./pages/admin/AuditLogPage";
import { UsersPage } from "./pages/admin/UsersPage";

function App() {
  return (
    <Router>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route element={<ProtectedRoute />}>
              <Route element={<AppShell />}>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/classic" element={<ClassicPage />} />

                <Route path="/bids" element={<BidsPage />} />
                <Route path="/bids/:id" element={<BidDetailPage />} />
                <Route element={<RoleRoute requires="editor" />}>
                  <Route path="/bids/new" element={<CreateBidPage />} />
                </Route>

                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/sessions" element={<SessionsPage />} />
                <Route path="/notifications" element={<NotificationsPage />} />

                <Route element={<RoleRoute requires="admin" />}>
                  <Route path="/admin/sync" element={<SyncHistoryPage />} />
                  <Route path="/admin/audit" element={<AuditLogPage />} />
                  <Route path="/admin/users" element={<UsersPage />} />
                </Route>

                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Route>
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
