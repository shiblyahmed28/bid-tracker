import { useEffect, useState } from "react";

import { fetchUsers, type AdminUser } from "../api/accounts";
import {
  createSettingsPerson,
  fetchSettingsPeople,
  updateSettingsPerson,
  type PersonType,
  type SettingsPerson,
} from "../api/settings";
import { useToast } from "../components/ToastContext";
import { Skeleton } from "../dashboard/Skeleton";
import { PersonHistoryModal } from "./PersonHistoryModal";
import { PersonMergeModal } from "./PersonMergeModal";

interface EditForm {
  canonical_name: string;
  email: string;
  person_type: PersonType;
  organization: string;
  phone: string;
  user: number | null;
}

function toEditForm(person: SettingsPerson): EditForm {
  return {
    canonical_name: person.canonical_name,
    email: person.email ?? "",
    person_type: person.person_type,
    organization: person.organization,
    phone: person.phone,
    user: person.user,
  };
}

/** §Phase 20 items 1-3 — the enhanced "Engaged Resources" management screen
 * (label change only; the model stays Person, §Phase 20 item 1). Item 4
 * (engagement history) and item 5 (welcome email) live in PersonHistoryModal;
 * item 3 (dedup/merge) lives in PersonMergeModal. */
export function EngagedResourcesPanel() {
  const { showToast } = useToast();
  const [rows, setRows] = useState<SettingsPerson[] | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [typeFilter, setTypeFilter] = useState<PersonType | "">("");
  const [activeFilter, setActiveFilter] = useState<"" | "true" | "false">("");

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<EditForm | null>(null);
  const [saving, setSaving] = useState(false);

  const [newName, setNewName] = useState("");
  const [adding, setAdding] = useState(false);

  const [historyPerson, setHistoryPerson] = useState<SettingsPerson | null>(null);
  const [showMerge, setShowMerge] = useState(false);

  function load() {
    setRows(null);
    fetchSettingsPeople({
      person_type: typeFilter || undefined,
      is_active: activeFilter === "" ? undefined : activeFilter === "true",
    }).then(setRows);
  }

  useEffect(load, [typeFilter, activeFilter]);
  useEffect(() => {
    fetchUsers().then(setUsers).catch(() => setUsers([]));
  }, []);

  async function handleAdd() {
    const trimmed = newName.trim();
    if (!trimmed) return;
    setAdding(true);
    try {
      await createSettingsPerson({ canonical_name: trimmed });
      setNewName("");
      showToast(`${trimmed} added`);
      load();
    } catch (err: any) {
      showToast(err?.response?.data?.canonical_name?.[0] ?? err?.response?.data?.detail ?? "Could not add that person.");
    } finally {
      setAdding(false);
    }
  }

  function startEdit(person: SettingsPerson) {
    setEditingId(person.id);
    setEditForm(toEditForm(person));
  }

  function patchEditForm(field: keyof EditForm, value: string | number | null) {
    setEditForm((prev) => (prev ? { ...prev, [field]: value } : prev));
  }

  async function saveEdit(person: SettingsPerson) {
    if (!editForm) return;
    setSaving(true);
    try {
      await updateSettingsPerson(person.id, {
        canonical_name: editForm.canonical_name.trim(),
        email: editForm.email.trim() || null,
        person_type: editForm.person_type,
        organization: editForm.organization.trim(),
        phone: editForm.phone.trim(),
        user: editForm.user,
      });
      showToast(`${editForm.canonical_name.trim()} saved`);
      setEditingId(null);
      load();
    } catch (err: any) {
      showToast(
        err?.response?.data?.canonical_name?.[0] ??
          err?.response?.data?.email?.[0] ??
          err?.response?.data?.detail ??
          "Could not save that change."
      );
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(person: SettingsPerson) {
    try {
      await updateSettingsPerson(person.id, { is_active: !person.is_active });
      showToast(`${person.canonical_name} ${person.is_active ? "deactivated" : "activated"}`);
      load();
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? "Could not update that record.");
    }
  }

  return (
    <div className="card">
      <div className="chead">
        <h2>Engaged Resources</h2>
        <span className="scope">{rows?.length ?? "…"} records</span>
        <div className="hgap" />
        <button className="btn btn-s btn-sm" onClick={() => setShowMerge(true)}>
          Check for duplicates
        </button>
      </div>

      <div className="cbody" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input
          className="inp"
          style={{ flex: "1 1 220px" }}
          placeholder="New engaged resource name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleAdd();
          }}
        />
        <button className="btn btn-p" onClick={handleAdd} disabled={adding || !newName.trim()}>
          {adding ? "Adding…" : "Add engaged resource"}
        </button>
      </div>

      <div className="cbody" style={{ display: "flex", gap: 8 }}>
        <select className="inp" style={{ width: "auto" }} value={typeFilter} onChange={(e) => setTypeFilter(e.target.value as PersonType | "")}>
          <option value="">All types</option>
          <option value="internal">Internal</option>
          <option value="external">External</option>
        </select>
        <select
          className="inp"
          style={{ width: "auto" }}
          value={activeFilter}
          onChange={(e) => setActiveFilter(e.target.value as "" | "true" | "false")}
        >
          <option value="">Active + inactive</option>
          <option value="true">Active only</option>
          <option value="false">Inactive only</option>
        </select>
      </div>

      <div className="tscroll tall">
        {rows === null ? (
          <div className="cbody">
            <Skeleton height={280} />
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Type</th>
                <th>Organization</th>
                <th>Phone</th>
                <th>Linked user</th>
                <th className="num">Usage</th>
                <th>Active</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((person) => {
                const isEditing = editingId === person.id;
                const form = isEditing ? editForm : null;
                return (
                  <tr key={person.id}>
                    <td>
                      {isEditing && form ? (
                        <input className="inp" value={form.canonical_name} onChange={(e) => patchEditForm("canonical_name", e.target.value)} />
                      ) : (
                        person.canonical_name
                      )}
                    </td>
                    <td>
                      {isEditing && form ? (
                        <input className="inp" value={form.email} onChange={(e) => patchEditForm("email", e.target.value)} />
                      ) : (
                        person.email ?? "—"
                      )}
                    </td>
                    <td>
                      {isEditing && form ? (
                        <select className="inp" value={form.person_type} onChange={(e) => patchEditForm("person_type", e.target.value)}>
                          <option value="internal">Internal</option>
                          <option value="external">External</option>
                        </select>
                      ) : (
                        <span className={`tag ${person.person_type === "external" ? "t-pend" : "t-no"}`}>
                          {person.person_type === "external" ? "External" : "Internal"}
                        </span>
                      )}
                    </td>
                    <td>
                      {isEditing && form ? (
                        <input className="inp" value={form.organization} onChange={(e) => patchEditForm("organization", e.target.value)} />
                      ) : (
                        person.organization || "—"
                      )}
                    </td>
                    <td>
                      {isEditing && form ? (
                        <input className="inp" value={form.phone} onChange={(e) => patchEditForm("phone", e.target.value)} />
                      ) : (
                        person.phone || "—"
                      )}
                    </td>
                    <td>
                      {isEditing && form ? (
                        <select
                          className="inp"
                          value={form.user ?? ""}
                          onChange={(e) => patchEditForm("user", e.target.value ? Number(e.target.value) : null)}
                        >
                          <option value="">— none —</option>
                          {users.map((u) => (
                            <option key={u.id} value={u.id}>
                              {u.full_name || u.email}
                            </option>
                          ))}
                        </select>
                      ) : (
                        person.user_full_name || person.user_email || "—"
                      )}
                    </td>
                    <td className="num">{person.usage_count}</td>
                    <td>
                      <div className={`toggle${person.is_active ? " on" : ""}`} onClick={() => toggleActive(person)} />
                    </td>
                    <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                      {isEditing ? (
                        <>
                          <button className="btn btn-p btn-sm" onClick={() => saveEdit(person)} disabled={saving}>
                            {saving ? "Saving…" : "Save"}
                          </button>{" "}
                          <button className="btn btn-s btn-sm" onClick={() => setEditingId(null)} disabled={saving}>
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          <button className="btn btn-s btn-sm" onClick={() => setHistoryPerson(person)}>
                            History
                          </button>{" "}
                          <button className="btn btn-s btn-sm" onClick={() => startEdit(person)}>
                            Edit
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {historyPerson && <PersonHistoryModal person={historyPerson} onClose={() => setHistoryPerson(null)} />}
      {showMerge && <PersonMergeModal onClose={() => setShowMerge(false)} onMerged={load} />}
    </div>
  );
}
