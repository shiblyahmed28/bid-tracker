import type { AdminUser } from "../api/accounts";

interface UserMultiSelectProps {
  users: AdminUser[];
  selectedIds: number[];
  onChange: (ids: number[]) => void;
}

/** Extra specific users beyond whatever a role multi-select already covers
 * — e.g. "Kaji and Nazmul also get the 21-day reminder" (§Phase 16). */
export function UserMultiSelect({ users, selectedIds, onChange }: UserMultiSelectProps) {
  function toggle(id: number) {
    onChange(selectedIds.includes(id) ? selectedIds.filter((x) => x !== id) : [...selectedIds, id]);
  }

  return (
    <div
      className="colgrid"
      style={{ maxHeight: 140, overflowY: "auto", border: "1px solid var(--line)", borderRadius: 8, padding: 8 }}
    >
      {users.map((u) => (
        <label className="colchk" key={u.id}>
          <input type="checkbox" checked={selectedIds.includes(u.id)} onChange={() => toggle(u.id)} />
          {u.full_name || u.email}
        </label>
      ))}
    </div>
  );
}
