import { useState } from "react";

import { ListsTab } from "../../settings/ListsTab";
import { NotificationsSettingsTab } from "../../settings/NotificationsSettingsTab";
import { PermissionsTab } from "../../settings/PermissionsTab";
import { SyncSettingsTab } from "../../settings/SyncSettingsTab";
import { TabBar, type TabDef } from "../../settings/TabBar";

const TABS: TabDef[] = [
  { key: "lists", label: "Lists" },
  { key: "permissions", label: "Users & permissions" },
  { key: "notifications", label: "Notifications" },
  { key: "sync", label: "Sheet sync" },
];

export function SettingsPage() {
  const [active, setActive] = useState("lists");

  return (
    <>
      <TabBar tabs={TABS} active={active} onChange={setActive} />
      {active === "lists" && <ListsTab />}
      {active === "permissions" && <PermissionsTab />}
      {active === "notifications" && <NotificationsSettingsTab />}
      {active === "sync" && <SyncSettingsTab />}
    </>
  );
}
