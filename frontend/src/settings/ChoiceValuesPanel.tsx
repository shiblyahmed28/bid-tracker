import { useEffect, useState } from "react";

import {
  createChoiceValue,
  fetchChoiceValues,
  reorderChoiceValues,
  updateChoiceValue,
  type ChoiceValueItem,
} from "../api/settings";
import { Skeleton } from "../dashboard/Skeleton";
import { useToast } from "../components/ToastContext";
import { DeactivateValueModal } from "./DeactivateValueModal";
import { RenameValueModal } from "./RenameValueModal";

interface ChoiceValuesPanelProps {
  listKey: string;
  listLabel: string;
  onCountChange: (count: number) => void;
}

export function ChoiceValuesPanel({ listKey, listLabel, onCountChange }: ChoiceValuesPanelProps) {
  const { showToast } = useToast();
  const [values, setValues] = useState<ChoiceValueItem[] | null>(null);
  const [renameTarget, setRenameTarget] = useState<ChoiceValueItem | null>(null);
  const [deactivateTarget, setDeactivateTarget] = useState<ChoiceValueItem | null>(null);
  const [dragId, setDragId] = useState<number | null>(null);

  const [newValue, setNewValue] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [adding, setAdding] = useState(false);

  function load() {
    setValues(null);
    fetchChoiceValues(listKey).then((rows) => {
      setValues(rows);
      onCountChange(rows.length);
    });
  }

  useEffect(load, [listKey]);

  async function handleAdd() {
    if (!newValue.trim()) return;
    setAdding(true);
    try {
      await createChoiceValue(listKey, { value: newValue.trim(), label: (newLabel || newValue).trim() });
      setNewValue("");
      setNewLabel("");
      showToast(`${newValue.trim()} added`);
      load();
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? "Could not add that value.");
    } finally {
      setAdding(false);
    }
  }

  async function handleToggleActive(value: ChoiceValueItem) {
    if (value.is_active) {
      setDeactivateTarget(value);
      return;
    }
    try {
      await updateChoiceValue(listKey, value.id, { is_active: true });
      showToast(`${value.label} reactivated`);
      load();
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? "Could not reactivate that value.");
    }
  }

  async function confirmDeactivate() {
    if (!deactivateTarget) return;
    try {
      await updateChoiceValue(listKey, deactivateTarget.id, { is_active: false });
      showToast(`${deactivateTarget.label} deactivated`);
      load();
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? "Could not deactivate that value.");
    } finally {
      setDeactivateTarget(null);
    }
  }

  function handleDrop(targetId: number) {
    if (dragId === null || dragId === targetId || !values) return;
    const reordered = [...values];
    const fromIdx = reordered.findIndex((v) => v.id === dragId);
    const toIdx = reordered.findIndex((v) => v.id === targetId);
    const [moved] = reordered.splice(fromIdx, 1);
    reordered.splice(toIdx, 0, moved);
    setValues(reordered);
    setDragId(null);
    reorderChoiceValues(listKey, reordered.map((v) => v.id)).catch((err: any) => {
      showToast(err?.response?.data?.detail ?? "Could not save the new order.");
      load();
    });
  }

  return (
    <div className="card">
      <div className="chead">
        <h2>{listLabel}</h2>
        <span className="scope">{values?.length ?? "…"} values</span>
      </div>
      <div className="cbody" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input
          className="inp"
          style={{ flex: "1 1 160px" }}
          placeholder="New value"
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
        />
        <input
          className="inp"
          style={{ flex: "1 1 160px" }}
          placeholder="Display label (optional)"
          value={newLabel}
          onChange={(e) => setNewLabel(e.target.value)}
        />
        <button className="btn btn-p" onClick={handleAdd} disabled={adding || !newValue.trim()}>
          {adding ? "Adding…" : "Add value"}
        </button>
      </div>
      <div className="tscroll">
        {values === null ? (
          <div className="cbody">
            <Skeleton height={220} />
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th></th>
                <th>Label</th>
                <th>Stored value</th>
                <th style={{ textAlign: "right" }}>Usage</th>
                <th>Active</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {values.map((v) => (
                <tr
                  key={v.id}
                  draggable
                  onDragStart={() => setDragId(v.id)}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => handleDrop(v.id)}
                  style={{ opacity: dragId === v.id ? 0.5 : 1 }}
                >
                  <td className="drag-handle" title="Drag to reorder">
                    ⠿
                  </td>
                  <td>
                    <b>{v.label}</b>
                    {v.created_by_sync && <span className="tag t-pend" style={{ marginLeft: 6 }}>from sheet</span>}
                  </td>
                  <td className="num" style={{ fontSize: 11.5 }}>
                    {v.value}
                  </td>
                  <td className="num" style={{ textAlign: "right" }}>
                    {v.usage_count}
                  </td>
                  <td>
                    <div className={`toggle${v.is_active ? " on" : ""}`} onClick={() => handleToggleActive(v)} />
                  </td>
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    <button className="btn btn-s btn-sm" onClick={() => setRenameTarget(v)}>
                      {v.created_by_sync ? "Review" : "Rename"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {renameTarget && (
        <RenameValueModal
          listKey={listKey}
          listLabel={listLabel}
          value={renameTarget}
          onClose={() => setRenameTarget(null)}
          onRenamed={() => {
            setRenameTarget(null);
            load();
          }}
        />
      )}
      {deactivateTarget && (
        <DeactivateValueModal
          value={deactivateTarget}
          onClose={() => setDeactivateTarget(null)}
          onConfirm={confirmDeactivate}
        />
      )}
    </div>
  );
}
