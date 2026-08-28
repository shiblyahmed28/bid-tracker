import type { Role } from "../auth/AuthContext";

const ROLES: Role[] = ["admin", "editor", "viewer"];
const LABEL: Record<Role, string> = { admin: "Admin", editor: "Editor", viewer: "Viewer" };

interface RoleMultiSelectProps {
  value: Role[];
  onChange: (roles: Role[]) => void;
}

export function RoleMultiSelect({ value, onChange }: RoleMultiSelectProps) {
  function toggle(role: Role) {
    onChange(value.includes(role) ? value.filter((r) => r !== role) : [...value, role]);
  }

  return (
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
      {ROLES.map((role) => (
        <label key={role} className="colchk" style={{ minWidth: "auto" }}>
          <input type="checkbox" checked={value.includes(role)} onChange={() => toggle(role)} />
          {LABEL[role]}
        </label>
      ))}
    </div>
  );
}
