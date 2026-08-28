import { useState } from "react";

import type { PersonRef } from "../api/bids";

interface EngagedResourcesSelectProps {
  people: PersonRef[];
  selectedIds: number[];
  onChange: (ids: number[]) => void;
}

/** A multi-select showing a live count (§11) — a search box narrows a
 * checkbox list rather than a native <select multiple>, which is both hard
 * to use with many options and doesn't show a running count on its own. */
export function EngagedResourcesSelect({ people, selectedIds, onChange }: EngagedResourcesSelectProps) {
  const [search, setSearch] = useState("");
  const filtered = search
    ? people.filter((p) => p.canonical_name.toLowerCase().includes(search.toLowerCase()))
    : people;

  function toggle(id: number) {
    onChange(selectedIds.includes(id) ? selectedIds.filter((x) => x !== id) : [...selectedIds, id]);
  }

  return (
    <div className="field">
      <label>
        Engaged resources{" "}
        <span style={{ textTransform: "none", fontWeight: 400, color: "var(--muted)" }}>
          ({selectedIds.length} selected)
        </span>
      </label>
      <input
        className="inp"
        placeholder="Search people…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{ marginBottom: 6 }}
      />
      <div
        className="colgrid"
        style={{ maxHeight: 180, overflowY: "auto", border: "1px solid var(--line)", borderRadius: 8, padding: 8 }}
      >
        {filtered.map((person) => (
          <label className="colchk" key={person.id}>
            <input type="checkbox" checked={selectedIds.includes(person.id)} onChange={() => toggle(person.id)} />
            {person.canonical_name}
          </label>
        ))}
        {filtered.length === 0 && <span className="hint">No matches.</span>}
      </div>
    </div>
  );
}
