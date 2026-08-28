import type { DistinctOption } from "../api/bids";
import { FILTERABLE_CONTAINS_COLUMNS, FILTERABLE_ENUM_COLUMNS } from "./columns";

interface FilterPanelProps {
  filters: Record<string, string>;
  options: Record<string, DistinctOption[]>;
  onChange: (param: string, value: string) => void;
}

export function FilterPanel({ filters, options, onChange }: FilterPanelProps) {
  return (
    <div className="panel">
      <h3>Filter by column value</h3>
      <div className="fgrid">
        {FILTERABLE_ENUM_COLUMNS.map((column) => (
          <div key={column.key}>
            <label>{column.label}</label>
            <select
              className="inp"
              value={filters[column.filterParam!] ?? ""}
              onChange={(e) => onChange(column.filterParam!, e.target.value)}
            >
              <option value="">All</option>
              {(options[column.filterParam!] ?? []).map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        ))}
        {FILTERABLE_CONTAINS_COLUMNS.map((column) => (
          <div key={column.key}>
            <label>{column.label} contains</label>
            <input
              className="inp"
              value={filters[column.filterParam!] ?? ""}
              onChange={(e) => onChange(column.filterParam!, e.target.value)}
            />
          </div>
        ))}
      </div>
      <p className="hint" style={{ marginTop: 9 }}>
        Date filtering uses the range bar below, which applies to the submission date.
      </p>
    </div>
  );
}
