export interface TabDef {
  key: string;
  label: string;
}

interface TabBarProps {
  tabs: TabDef[];
  active: string;
  onChange: (key: string) => void;
}

/** Renders both a button row and a <select> — CSS (§Phase 16: "tabs become
 * a select" at 380px) picks which is visible, so there's one source of
 * truth for tab state either way. */
export function TabBar({ tabs, active, onChange }: TabBarProps) {
  return (
    <div className="settings-tabbar">
      <div className="tabbar-buttons">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            className={`tabbar-btn${tab.key === active ? " active" : ""}`}
            onClick={() => onChange(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <select className="inp tabbar-select" value={active} onChange={(e) => onChange(e.target.value)}>
        {tabs.map((tab) => (
          <option key={tab.key} value={tab.key}>
            {tab.label}
          </option>
        ))}
      </select>
    </div>
  );
}
