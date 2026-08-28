import { useState } from "react";

import type { ChoiceValueItem } from "../api/settings";
import { Modal } from "../components/Modal";

interface DeactivateValueModalProps {
  value: ChoiceValueItem;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export function DeactivateValueModal({ value, onClose, onConfirm }: DeactivateValueModalProps) {
  const [saving, setSaving] = useState(false);

  async function handleConfirm() {
    setSaving(true);
    try {
      await onConfirm();
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Deactivate "${value.label}"?`}
      footer={
        <>
          <button className="btn btn-s" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button className="btn btn-d" onClick={handleConfirm} disabled={saving}>
            {saving ? "Deactivating…" : "Deactivate"}
          </button>
        </>
      }
    >
      <p style={{ fontSize: 13, lineHeight: 1.6 }}>
        Existing bids using <b>{value.value}</b> keep it exactly as-is — nothing about them changes.
        {value.usage_count > 0 && (
          <>
            {" "}
            <b>{value.usage_count}</b> bid record{value.usage_count === 1 ? "" : "s"} currently use it.
          </>
        )}
      </p>
      <p style={{ fontSize: 13, lineHeight: 1.6, marginTop: 8 }}>
        It just disappears from the dropdown for anything created or edited from now on.
      </p>
    </Modal>
  );
}
