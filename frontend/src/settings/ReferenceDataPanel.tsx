import { useEffect, useState } from "react";

import {
  createSettingsClient,
  createSettingsPerson,
  createSettingsTeam,
  fetchSettingsClients,
  fetchSettingsPeople,
  fetchSettingsTeams,
  updateSettingsClient,
  updateSettingsPerson,
  updateSettingsTeam,
  type SettingsClient,
  type SettingsPerson,
  type SettingsTeam,
} from "../api/settings";
import { Skeleton } from "../dashboard/Skeleton";
import { useToast } from "../components/ToastContext";

type Kind = "clients" | "people" | "teams";
type Row = SettingsClient | SettingsPerson | SettingsTeam;

const LABELS: Record<Kind, string> = { clients: "Clients", people: "People", teams: "Teams" };
const SINGULAR: Record<Kind, string> = { clients: "client", people: "person", teams: "team" };
const PLACEHOLDER: Record<Kind, string> = {
  clients: "New client name",
  people: "New person name",
  teams: "New team name",
};

function nameOf(kind: Kind, row: Row): string {
  return kind === "people" ? (row as SettingsPerson).canonical_name : (row as SettingsClient | SettingsTeam).name;
}

// The create endpoints validate on `name` (clients/teams) or
// `canonical_name` (people) as a field-level error, which DRF returns as
// {field: [message]} rather than {detail: message} — check both shapes so
// the toast still surfaces the specific reason (e.g. "already exists")
// instead of the generic fallback.
function firstErrorMessage(data: any): string | undefined {
  return data?.detail ?? data?.name?.[0] ?? data?.canonical_name?.[0];
}

interface ReferenceDataPanelProps {
  kind: Kind;
  onCountChange: (count: number) => void;
}

export function ReferenceDataPanel({ kind, onCountChange }: ReferenceDataPanelProps) {
  const { showToast } = useToast();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const [newName, setNewName] = useState("");
  const [adding, setAdding] = useState(false);

  function load() {
    setRows(null);
    const fetcher = kind === "clients" ? fetchSettingsClients : kind === "people" ? fetchSettingsPeople : fetchSettingsTeams;
    fetcher().then((data) => {
      setRows(data);
      onCountChange(data.length);
    });
  }

  useEffect(load, [kind]);

  function startEdit(row: Row) {
    setEditingId(row.id);
    setEditValue(nameOf(kind, row));
  }

  async function saveEdit(row: Row) {
    const trimmed = editValue.trim();
    setEditingId(null);
    if (!trimmed || trimmed === nameOf(kind, row)) return;

    try {
      if (kind === "clients") await updateSettingsClient(row.id, { name: trimmed });
      else if (kind === "people") await updateSettingsPerson(row.id, { canonical_name: trimmed });
      else await updateSettingsTeam(row.id, { name: trimmed });

      showToast(`${trimmed} saved`);
      load();
    } catch (err: any) {
      showToast(firstErrorMessage(err?.response?.data) ?? "Could not save that change.");
    }
  }

  async function handleAdd() {
    const trimmed = newName.trim();
    if (!trimmed) return;
    setAdding(true);
    try {
      if (kind === "clients") await createSettingsClient({ name: trimmed });
      else if (kind === "people") await createSettingsPerson({ canonical_name: trimmed });
      else await createSettingsTeam({ name: trimmed });

      setNewName("");
      showToast(`${trimmed} added`);
      load();
    } catch (err: any) {
      showToast(firstErrorMessage(err?.response?.data) ?? `Could not add that ${SINGULAR[kind]}.`);
    } finally {
      setAdding(false);
    }
  }

  async function toggleTeamActive(row: SettingsTeam) {
    try {
      await updateSettingsTeam(row.id, { is_active: !row.is_active });
      showToast(`${row.name} ${row.is_active ? "deactivated" : "activated"}`);
      load();
    } catch (err: any) {
      showToast(firstErrorMessage(err?.response?.data) ?? "Could not update that team.");
    }
  }

  return (
    <div className="card">
      <div className="chead">
        <h2>{LABELS[kind]}</h2>
        <span className="scope">{rows?.length ?? "…"} records</span>
      </div>
      <div className="cbody" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input
          className="inp"
          style={{ flex: "1 1 220px" }}
          placeholder={PLACEHOLDER[kind]}
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleAdd();
          }}
        />
        <button className="btn btn-p" onClick={handleAdd} disabled={adding || !newName.trim()}>
          {adding ? "Adding…" : `Add ${SINGULAR[kind]}`}
        </button>
      </div>
      <div className="tscroll tall">
        {rows === null ? (
          <div className="cbody">
            <Skeleton height={220} />
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>{kind === "people" ? "Name" : "Name"}</th>
                <th style={{ textAlign: "right" }}>Usage</th>
                {kind === "teams" && <th>Active</th>}
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>
                    {editingId === row.id ? (
                      <input
                        className="inp"
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") saveEdit(row);
                          if (e.key === "Escape") setEditingId(null);
                        }}
                        onBlur={() => saveEdit(row)}
                      />
                    ) : (
                      nameOf(kind, row)
                    )}
                  </td>
                  <td className="num" style={{ textAlign: "right" }}>
                    {(row as any).usage_count}
                  </td>
                  {kind === "teams" && (
                    <td>
                      <div
                        className={`toggle${(row as SettingsTeam).is_active ? " on" : ""}`}
                        onClick={() => toggleTeamActive(row as SettingsTeam)}
                      />
                    </td>
                  )}
                  <td style={{ textAlign: "right" }}>
                    {editingId !== row.id && (
                      <button className="btn btn-s btn-sm" onClick={() => startEdit(row)}>
                        Rename
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
