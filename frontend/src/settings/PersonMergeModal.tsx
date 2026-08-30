import { useEffect, useState } from "react";

import { fetchPersonDuplicates, mergePersons, type PersonDuplicateGroup, type SettingsPerson } from "../api/settings";
import { Modal } from "../components/Modal";
import { useToast } from "../components/ToastContext";
import { EmptyState, Skeleton } from "../dashboard/Skeleton";

interface PersonMergeModalProps {
  onClose: () => void;
  onMerged: () => void;
}

/** §Phase 20 item 3 — likely-duplicate groups by normalized name (whitespace
 * and casing variants of the same person), with a pick-the-survivor merge
 * action. The phase's own guidance: run this before turning on welcome
 * emails, so a duplicate record doesn't miss out on one. */
export function PersonMergeModal({ onClose, onMerged }: PersonMergeModalProps) {
  const { showToast } = useToast();
  const [groups, setGroups] = useState<PersonDuplicateGroup[] | null>(null);
  const [survivorByGroup, setSurvivorByGroup] = useState<Record<number, number>>({});
  const [merging, setMerging] = useState<number | null>(null);

  function load() {
    setGroups(null);
    fetchPersonDuplicates().then(setGroups);
  }

  useEffect(load, []);

  function groupKey(group: PersonDuplicateGroup, index: number) {
    return group.people[0]?.id ?? index;
  }

  function survivorFor(group: PersonDuplicateGroup, index: number): number {
    return survivorByGroup[groupKey(group, index)] ?? group.people[0].id;
  }

  async function handleMerge(group: PersonDuplicateGroup, index: number) {
    const survivorId = survivorFor(group, index);
    const duplicates = group.people.filter((p) => p.id !== survivorId);
    setMerging(groupKey(group, index));
    try {
      for (const duplicate of duplicates) {
        await mergePersons(survivorId, duplicate.id);
      }
      showToast("Merged");
      onMerged();
      load();
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? "Could not merge those records.");
    } finally {
      setMerging(null);
    }
  }

  return (
    <Modal open onClose={onClose} title="Merge duplicate engaged resources">
      <p style={{ fontSize: 13, lineHeight: 1.6, marginBottom: 14 }}>
        Grouped by normalized name — whitespace and casing variants of the same person. Pick which record
        survives; every engagement, plus any CAM/sales resource/bid manager reference, moves onto it. The
        other record is deactivated, not deleted.
      </p>

      {groups === null ? (
        <Skeleton height={160} />
      ) : groups.length === 0 ? (
        <EmptyState message="No likely duplicates found" />
      ) : (
        groups.map((group, index) => {
          const survivorId = survivorFor(group, index);
          return (
            <div key={groupKey(group, index)} className="form-section">
              {group.people.map((person: SettingsPerson) => (
                <label
                  key={person.id}
                  style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, padding: "4px 0" }}
                >
                  <input
                    type="radio"
                    name={`survivor-${groupKey(group, index)}`}
                    checked={survivorId === person.id}
                    onChange={() => setSurvivorByGroup((prev) => ({ ...prev, [groupKey(group, index)]: person.id }))}
                  />
                  <b>{person.canonical_name}</b>
                  <span className="hint" style={{ textTransform: "none" }}>
                    {person.usage_count} bid{person.usage_count === 1 ? "" : "s"}
                    {person.email ? ` · ${person.email}` : ""}
                  </span>
                </label>
              ))}
              <button
                className="btn btn-p btn-sm"
                style={{ marginTop: 8 }}
                disabled={merging === groupKey(group, index)}
                onClick={() => handleMerge(group, index)}
              >
                {merging === groupKey(group, index) ? "Merging…" : "Merge into selected"}
              </button>
            </div>
          );
        })
      )}
    </Modal>
  );
}
