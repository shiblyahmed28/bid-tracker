import type { DistinctOption } from "../api/bids";
import { COLUMNS } from "./columns";

interface ActiveFilterChipsProps {
  filters: Record<string, string>;
  options: Record<string, DistinctOption[]>;
  onRemove: (param: string) => void;
  onClearAll: () => void;
}

export function labelFor(param: string, value: string, options: Record<string, DistinctOption[]>) {
  const column = COLUMNS.find((c) => c.filterParam === param);
  const match = options[param]?.find((opt) => opt.value === value);
  return `${column?.label ?? param}: ${match?.label ?? value}`;
}

export function ActiveFilterChips({ filters, options, onRemove, onClearAll }: ActiveFilterChipsProps) {
  const entries = Object.entries(filters).filter(([, value]) => value);
  if (!entries.length) return null;

  return (
    <div className="chiplist active-filter-chips">
      {entries.map(([param, value]) => (
        <span className="mini removable-chip" key={param}>
          {labelFor(param, value, options)}
          <button onClick={() => onRemove(param)} aria-label={`Remove filter: ${labelFor(param, value, options)}`}>
            ×
          </button>
        </span>
      ))}
      <button className="mini removable-chip clear-all" onClick={onClearAll}>
        Clear all
      </button>
    </div>
  );
}
