import { useState } from "react";

import { renameChoiceValue, type ChoiceValueItem } from "../api/settings";
import { Modal } from "../components/Modal";
import { useToast } from "../components/ToastContext";

interface RenameValueModalProps {
  listKey: string;
  listLabel: string;
  value: ChoiceValueItem;
  onClose: () => void;
  onRenamed: (updated: ChoiceValueItem) => void;
}

export function RenameValueModal({ listKey, listLabel, value, onClose, onRenamed }: RenameValueModalProps) {
  const { showToast } = useToast();
  const [newValue, setNewValue] = useState(value.value);
  const [newLabel, setNewLabel] = useState(value.label);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setSaving(true);
    setError(null);
    try {
      const result = await renameChoiceValue(listKey, value.id, newValue, newLabel);
      showToast(
        result.updated_bids > 0
          ? `Renamed — ${result.updated_bids} bid record${result.updated_bids === 1 ? "" : "s"} updated`
          : "Renamed"
      );
      onRenamed(result.value);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Something went wrong. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Rename value — ${listLabel}`}
      footer={
        <>
          <button className="btn btn-s" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button className="btn btn-p" onClick={handleSubmit} disabled={saving || !newValue}>
            {saving ? "Renaming…" : "Rename"}
          </button>
        </>
      }
    >
      <div className="field">
        <label className="req">Stored value</label>
        <input value={newValue} onChange={(e) => setNewValue(e.target.value)} />
      </div>
      <div className="field">
        <label>Display label</label>
        <input value={newLabel} onChange={(e) => setNewLabel(e.target.value)} />
      </div>

      {error && <p className="err">{error}</p>}

      <div className="banner b-warn" style={{ marginTop: 14 }}>
        {value.usage_count > 0 ? (
          <>
            This will update <b>{value.usage_count}</b> bid record{value.usage_count === 1 ? "" : "s"} currently
            using <b>{value.value}</b>.
          </>
        ) : (
          <>No bids currently use this value — only the list entry itself will change.</>
        )}
      </div>
    </Modal>
  );
}
