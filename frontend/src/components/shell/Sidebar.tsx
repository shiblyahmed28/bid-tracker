import { NavLink, useLocation } from "react-router-dom";

import { type Role, useAuth } from "../../auth/AuthContext";
import { SignOutIcon } from "../../icons";
import { type NavItem, NAV_GROUPS } from "./navConfig";

const ROLE_RANK: Record<Role, number> = { viewer: 0, editor: 1, admin: 2 };

function meetsRole(userRole: Role, minRole?: Role) {
  if (!minRole) return true;
  return ROLE_RANK[userRole] >= ROLE_RANK[minRole];
}

function meetsCapability(userCapabilities: string[], capability?: string) {
  if (!capability) return true;
  return userCapabilities.includes(capability);
}

/** Exactly one nav item is ever active (§18 Phase 18 item 6). A plain
 * prefix-matching NavLink would mark both "/bids" and "/bids/new" active on
 * /bids/new, since "/bids/new" starts with "/bids/". Instead, among every
 * visible item whose `to` matches the current path (exactly, or as a path
 * segment prefix — so a route with no nav item of its own, like a bid
 * detail page, still highlights its nearest parent), only the longest — most
 * specific — match wins. */
function findActiveTo(items: NavItem[], pathname: string): string | undefined {
  const matches = items.filter((item) => pathname === item.to || pathname.startsWith(`${item.to}/`));
  matches.sort((a, b) => b.to.length - a.to.length);
  return matches[0]?.to;
}

interface SidebarProps {
  open: boolean;
  onNavigate: () => void;
}

export function Sidebar({ open, onNavigate }: SidebarProps) {
  const { user, logout } = useAuth();
  const location = useLocation();
  if (!user) return null;

  const visibleGroups = NAV_GROUPS.filter((group) => meetsRole(user.role, group.minRole)).map((group) => ({
    ...group,
    items: group.items.filter(
      (item) => meetsRole(user.role, item.minRole) && meetsCapability(user.capabilities, item.capability)
    ),
  }));
  const activeTo = findActiveTo(
    visibleGroups.flatMap((group) => group.items),
    location.pathname
  );

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
        {visibleGroups.map((group) => {
          if (group.items.length === 0) return null;
          return (
            <div key={group.label}>
              <div className="nav-group-label">{group.label}</div>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onNavigate}
                  className={`nav-item${item.to === activeTo ? " active" : ""}`}
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
