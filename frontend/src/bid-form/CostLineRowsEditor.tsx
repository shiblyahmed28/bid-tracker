export interface CostLineRow {
  description: string;
  date: string;
  reference: string;
  amount: string;
  currency: "BDT" | "USD";
}

export const EMPTY_COST_LINE_ROW: CostLineRow = {
  description: "",
  date: "",
  reference: "",
  amount: "",
  currency: "BDT",
};

interface CostLineRowsEditorProps {
  rows: CostLineRow[];
  onChange: (rows: CostLineRow[]) => void;
}

/** §Phase 22 item 4 — a repeatable cost-line row with live totals, split by
 * currency (never summed together, §8/§20). */
export function CostLineRowsEditor({ rows, onChange }: CostLineRowsEditorProps) {
  function updateRow(index: number, patch: Partial<CostLineRow>) {
    onChange(rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  function addRow() {
    onChange([...rows, { ...EMPTY_COST_LINE_ROW }]);
  }

  function removeRow(index: number) {
    onChange(rows.filter((_, i) => i !== index));
  }

  const totalBdt = rows
    .filter((row) => row.currency === "BDT")
    .reduce((sum, row) => sum + (Number(row.amount) || 0), 0);
  const totalUsd = rows
    .filter((row) => row.currency === "USD")
    .reduce((sum, row) => sum + (Number(row.amount) || 0), 0);

  return (
    <div className="field">
      <label>
        Cost lines{" "}
        <span style={{ textTransform: "none", fontWeight: 400, color: "var(--muted)" }}>
          ({rows.length})
        </span>
      </label>

      {rows.length > 0 && (
        <div className="tscroll" style={{ marginBottom: 8 }}>
          <table>
            <thead>
              <tr>
                <th>Description</th>
                <th>Date</th>
                <th>Reference</th>
                <th className="num">Amount</th>
                <th>Currency</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index}>
                  <td>
                    <input
                      className="inp"
                      value={row.description}
                      onChange={(e) => updateRow(index, { description: e.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      className="inp"
                      type="date"
                      value={row.date}
                      onChange={(e) => updateRow(index, { date: e.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      className="inp"
                      value={row.reference}
                      onChange={(e) => updateRow(index, { reference: e.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      className="inp num"
                      type="number"
                      min="0"
                      step="0.01"
                      style={{ width: 100 }}
                      value={row.amount}
                      onChange={(e) => updateRow(index, { amount: e.target.value })}
                    />
                  </td>
                  <td>
                    <select
                      className="inp"
                      value={row.currency}
                      onChange={(e) => updateRow(index, { currency: e.target.value as "BDT" | "USD" })}
                    >
                      <option value="BDT">BDT</option>
                      <option value="USD">USD</option>
                    </select>
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
                <td className="num" colSpan={2}>
                  <b>
                    ৳{totalBdt.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    {totalUsd ? ` · $${totalUsd.toLocaleString("en-US", { minimumFractionDigits: 2 })}` : ""}
                  </b>
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      <button type="button" className="btn btn-s btn-sm" onClick={addRow}>
        + Add cost line
      </button>
    </div>
  );
}
