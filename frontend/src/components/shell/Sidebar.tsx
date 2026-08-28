import { NavLink } from "react-router-dom";

import { type Role, useAuth } from "../../auth/AuthContext";
import { SignOutIcon } from "../../icons";
import { NAV_GROUPS } from "./navConfig";

const ROLE_RANK: Record<Role, number> = { viewer: 0, editor: 1, admin: 2 };

function meetsRole(userRole: Role, minRole?: Role) {
  if (!minRole) return true;
  return ROLE_RANK[userRole] >= ROLE_RANK[minRole];
}

function meetsCapability(userCapabilities: string[], capability?: string) {
  if (!capability) return true;
  return userCapabilities.includes(capability);
}

interface SidebarProps {
  open: boolean;
  onNavigate: () => void;
}

export function Sidebar({ open, onNavigate }: SidebarProps) {
  const { user, logout } = useAuth();
  if (!user) return null;

  const initials = user.full_name
    ? user.full_name
        .split(/\s+/)
        .map((part) => part[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : user.email[0].toUpperCase();

  return (
    <aside className={`sidebar${open ? " open" : ""}`} id="sidebar">
      <div className="brand">
        <img src="/logo.png" alt="" />
        <div>
          <b>Spectrum</b>
          <span>Bid Tracker</span>
        </div>
      </div>

      <nav className="sidebar-nav" aria-label="Primary">
        {NAV_GROUPS.filter((group) => meetsRole(user.role, group.minRole)).map((group) => {
          const items = group.items.filter(
            (item) => meetsRole(user.role, item.minRole) && meetsCapability(user.capabilities, item.capability)
          );
          if (items.length === 0) return null;
          return (
            <div key={group.label}>
              <div className="nav-group-label">{group.label}</div>
              {items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onNavigate}
                  className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
                >
                  <item.icon />
                  {item.label}
                </NavLink>
              ))}
            </div>
          );
        })}
      </nav>

      <div className="who">
        <div className="avatar">{initials}</div>
        <div className="who-text">
          <b>{user.full_name || user.email}</b>
          <span>{user.role}</span>
        </div>
        <button className="nav-item signout-btn" title="Sign out" onClick={logout}>
          <SignOutIcon />
        </button>
      </div>
    </aside>
  );
}
