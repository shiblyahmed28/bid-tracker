import { COLUMN_GROUPS, COLUMNS } from "./columns";

interface ColumnPickerProps {
  visibleKeys: string[];
  onToggle: (key: string) => void;
  onSelectAll: () => void;
  onResetToDefault: () => void;
}

export function ColumnPicker({ visibleKeys, onToggle, onSelectAll, onResetToDefault }: ColumnPickerProps) {
  const visible = new Set(visibleKeys);

  return (
    <div className="panel">
      <h3>Columns to display</h3>
      {COLUMN_GROUPS.map((group) => {
        const columns = COLUMNS.filter((c) => c.group === group);
        if (!columns.length) return null;
        return (
          <div key={group}>
            <p className="hint" style={{ margin: "9px 0 5px", fontWeight: 700, color: "var(--ink)" }}>
              {group}
            </p>
            <div className="colgrid">
              {columns.map((c) => (
                <label className={`colchk${c.isNew ? " new" : ""}`} key={c.key}>
                  <input type="checkbox" checked={visible.has(c.key)} onChange={() => onToggle(c.key)} />
                  {c.label}
                  {c.isNew && <small>new</small>}
                </label>
              ))}
            </div>
          </div>
        );
      })}
      <div style={{ display: "flex", gap: 7, marginTop: 11 }}>
        <button className="btn btn-s btn-sm" onClick={onSelectAll}>
          Select all
        </button>
        <button className="btn btn-s btn-sm" onClick={onResetToDefault}>
          Reset to default
        </button>
      </div>
    </div>
  );
}
