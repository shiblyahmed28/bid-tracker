import type { ComponentType, SVGProps } from "react";

import {
  BellIcon,
  DashIcon,
  GridIcon,
  KeyIcon,
  ListIcon,
  MailIcon,
  PlusIcon,
  SettingsIcon,
  ShieldIcon,
  SyncIcon,
  UserIcon,
  UsersIcon,
} from "../../icons";
import type { Role } from "../../auth/AuthContext";

export interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  minRole?: Role;
  /** Capability-gated instead of (or in addition to) role-gated — an admin
   * can grant this to a specific editor or viewer (§Phase 16). */
  capability?: string;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
  minRole?: Role;
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Dashboards",
    items: [
      { to: "/dashboard", label: "Dashboard", icon: DashIcon },
      { to: "/classic", label: "Classic view", icon: GridIcon },
    ],
  },
  {
    label: "Bids",
    items: [
      { to: "/bids", label: "All bids", icon: ListIcon },
      { to: "/bids/new", label: "Create bid", icon: PlusIcon, minRole: "editor" },
    ],
  },
  {
    label: "Account",
    items: [
      { to: "/profile", label: "My profile", icon: UserIcon },
      { to: "/sessions", label: "Login history", icon: KeyIcon },
      { to: "/notifications", label: "Notifications", icon: BellIcon },
    ],
  },
  {
    label: "Administration",
    items: [
      { to: "/admin/sync", label: "Sync history", icon: SyncIcon, capability: "view_sync_history" },
      { to: "/admin/audit", label: "Audit log", icon: ShieldIcon, capability: "view_audit_log" },
      { to: "/admin/email-log", label: "Email log", icon: MailIcon, capability: "view_email_log" },
      { to: "/admin/users", label: "Users", icon: UsersIcon, capability: "manage_users" },
      { to: "/settings", label: "Master settings", icon: SettingsIcon, capability: "access_master_settings" },
    ],
  },
];

interface PageMeta {
  match: (pathname: string) => boolean;
  title: string;
  crumb: string;
}

const PAGE_META: PageMeta[] = [
  { match: (p) => p === "/dashboard", title: "Dashboard", crumb: "Overview" },
  { match: (p) => p === "/classic", title: "Classic view", crumb: "Overview" },
  { match: (p) => p === "/bids/new", title: "Create bid", crumb: "Bids" },
  { match: (p) => p.startsWith("/bids/") && p !== "/bids/new", title: "Bid detail", crumb: "Bids" },
  { match: (p) => p === "/bids", title: "All bids", crumb: "Bids" },
  { match: (p) => p === "/profile", title: "My profile", crumb: "Account" },
  { match: (p) => p === "/sessions", title: "Login history", crumb: "Account" },
  { match: (p) => p === "/notifications", title: "Notifications", crumb: "Account" },
  { match: (p) => p === "/admin/sync", title: "Sync history", crumb: "Administration" },
  { match: (p) => p === "/admin/audit", title: "Audit log", crumb: "Administration" },
  { match: (p) => p === "/admin/email-log", title: "Email log", crumb: "Administration" },
  { match: (p) => p === "/admin/users", title: "Users", crumb: "Administration" },
  { match: (p) => p === "/settings", title: "Master settings", crumb: "Administration" },
];

export function pageMetaFor(pathname: string): { title: string; crumb: string } {
  return PAGE_META.find((entry) => entry.match(pathname)) ?? { title: "Spectrum Bid Tracker", crumb: "" };
}
