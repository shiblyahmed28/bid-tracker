import type { RailItem } from "./railConfig";

interface ListsRailProps {
  items: RailItem[];
  selectedKey: string;
  onSelect: (item: RailItem) => void;
}

function itemKey(item: RailItem): string {
  return `${item.kind}:${item.key}`;
}

export function ListsRail({ items, selectedKey, onSelect }: ListsRailProps) {
  return (
    <div className="settings-rail">
      {items.map((item) => (
        <button
          key={itemKey(item)}
          className={`settings-rail-item${itemKey(item) === selectedKey ? " active" : ""}`}
          onClick={() => onSelect(item)}
        >
          {item.label}
          {item.kind === "choice" && <span className="mini">{item.valuesCount}</span>}
        </button>
      ))}
    </div>
  );
}
