import type { PersonRef } from "../api/bids";

export interface EngagementRow {
  personId: number | "";
  engagedFrom: string;
  engagedTo: string;
  days: string;
  convenienceBill: string;
}

export const EMPTY_ENGAGEMENT_ROW: EngagementRow = {
  personId: "",
  engagedFrom: "",
  engagedTo: "",
  days: "",
  convenienceBill: "",
};

interface EngagementRowsEditorProps {
  people: PersonRef[];
  rows: EngagementRow[];
  onChange: (rows: EngagementRow[]) => void;
}

/** §Phase 22 item 4 — replaces the old checkbox-list engaged_resources
 * selector with a repeatable row carrying the per-person detail
 * (BidEngagement's own fields) directly, with live totals. Adding a person
 * and leaving every optional field blank is exactly equivalent to the old
 * "just check the box" (days=0, no dates, no convenience bill). */
export function EngagementRowsEditor({ people, rows, onChange }: EngagementRowsEditorProps) {
  function updateRow(index: number, patch: Partial<EngagementRow>) {
    onChange(rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  function addRow() {
    onChange([...rows, { ...EMPTY_ENGAGEMENT_ROW }]);
  }

  function removeRow(index: number) {
    onChange(rows.filter((_, i) => i !== index));
  }

  const totalDays = rows.reduce((sum, row) => sum + (Number(row.days) || 0), 0);
  const totalBill = rows.reduce((sum, row) => sum + (Number(row.convenienceBill) || 0), 0);

  return (
    <div className="field">
      <label>
        Engaged resources{" "}
        <span style={{ textTransform: "none", fontWeight: 400, color: "var(--muted)" }}>
          ({rows.length})
        </span>
      </label>

      {rows.length > 0 && (
        <div className="tscroll" style={{ marginBottom: 8 }}>
          <table>
            <thead>
              <tr>
                <th>Person</th>
                <th>From</th>
                <th>To</th>
                <th className="num">Days</th>
                <th className="num">Convenience bill</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index}>
                  <td>
                    <select
                      className="inp"
                      value={row.personId}
                      onChange={(e) =>
                        updateRow(index, { personId: e.target.value ? Number(e.target.value) : "" })
                      }
                    >
                      <option value="">— select —</option>
                      {people.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.canonical_name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      className="inp"
                      type="date"
                      value={row.engagedFrom}
                      onChange={(e) => updateRow(index, { engagedFrom: e.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      className="inp"
                      type="date"
                      value={row.engagedTo}
                      onChange={(e) => updateRow(index, { engagedTo: e.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      className="inp num"
                      type="number"
                      min="0"
                      style={{ width: 64 }}
                      value={row.days}
                      onChange={(e) => updateRow(index, { days: e.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      className="inp num"
                      type="number"
                      min="0"
                      step="0.01"
                      style={{ width: 100 }}
                      value={row.convenienceBill}
                      onChange={(e) => updateRow(index, { convenienceBill: e.target.value })}
                    />
                  </td>
                  <td>
                    <button type="button" className="btn btn-s btn-sm" onClick={() => removeRow(index)}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={3}>
                  <b>Total</b>
                </td>
                <td className="num">
                  <b>{totalDays}</b>
                </td>
                <td className="num">
                  <b>{totalBill.toLocaleString("en-US", { minimumFractionDigits: 2 })}</b>
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      <button type="button" className="btn btn-s btn-sm" onClick={addRow}>
        + Add engagement row
      </button>
    </div>
  );
}
