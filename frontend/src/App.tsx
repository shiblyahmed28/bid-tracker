import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import { AuthProvider } from "./auth/AuthContext";
import { CapabilityRoute } from "./auth/CapabilityRoute";
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
import { EmailLogPage } from "./pages/admin/EmailLogPage";
import { UsersPage } from "./pages/admin/UsersPage";
import { SettingsPage } from "./pages/admin/SettingsPage";

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

                <Route element={<CapabilityRoute requires="view_sync_history" />}>
                  <Route path="/admin/sync" element={<SyncHistoryPage />} />
                </Route>
                <Route element={<CapabilityRoute requires="view_audit_log" />}>
                  <Route path="/admin/audit" element={<AuditLogPage />} />
                </Route>
                <Route element={<CapabilityRoute requires="view_email_log" />}>
                  <Route path="/admin/email-log" element={<EmailLogPage />} />
                </Route>
                <Route element={<CapabilityRoute requires="manage_users" />}>
                  <Route path="/admin/users" element={<UsersPage />} />
                </Route>
                <Route element={<CapabilityRoute requires="access_master_settings" />}>
                  <Route path="/settings" element={<SettingsPage />} />
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
