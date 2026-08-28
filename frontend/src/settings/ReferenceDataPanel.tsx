import { useEffect, useState } from "react";

import {
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

function nameOf(kind: Kind, row: Row): string {
  return kind === "people" ? (row as SettingsPerson).canonical_name : (row as SettingsClient | SettingsTeam).name;
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
      showToast(err?.response?.data?.detail ?? "Could not save that change.");
    }
  }

  async function toggleTeamActive(row: SettingsTeam) {
    try {
      await updateSettingsTeam(row.id, { is_active: !row.is_active });
      showToast(`${row.name} ${row.is_active ? "deactivated" : "activated"}`);
      load();
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? "Could not update that team.");
    }
  }

  return (
    <div className="card">
      <div className="chead">
        <h2>{LABELS[kind]}</h2>
        <span className="scope">{rows?.length ?? "…"} records</span>
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
