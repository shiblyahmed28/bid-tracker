import type { BidDetail } from "../api/bids";
import { formatDMY } from "../lib/dateUtils";

function money(amount: number): string {
  return amount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function currencyPair(bdt: number, usd: number): string {
  return usd ? `৳${money(bdt)} · $${money(usd)}` : `৳${money(bdt)}`;
}

/** §Phase 22 item 2 — the full breakdown (engagement table, cost-line
 * table, management cost with both components visible), detail page only.
 * The dashboard and All-bids register only ever get the summary figure
 * (management_cost_bdt/usd) — see KpiCards and register/columns.tsx. */
export function CostBreakdown({ bid }: { bid: BidDetail }) {
  return (
    <div className="card">
      <div className="chead">
        <h2>Cost breakdown</h2>
        <span className="scope">Engagement + cost lines</span>
      </div>
      <div className="cbody">
        <h3 className="subhead">Engagement</h3>
        <div className="tscroll">
          <table>
            <thead>
              <tr>
                <th>Person</th>
                <th>Engaged from</th>
                <th>Engaged to</th>
                <th className="num">Days</th>
                <th className="num">Convenience bill</th>
                <th>Note</th>
              </tr>
            </thead>
            <tbody>
              {bid.engagements.length === 0 ? (
                <tr>
                  <td colSpan={6} className="hint">
                    No engaged resources recorded.
                  </td>
                </tr>
              ) : (
                bid.engagements.map((e) => (
                  <tr key={e.id}>
                    <td>{e.person.canonical_name}</td>
                    <td className="num">{formatDMY(e.engaged_from)}</td>
                    <td className="num">{formatDMY(e.engaged_to)}</td>
                    <td className="num">{e.days}</td>
                    <td className="num">{money(e.convenience_bill)}</td>
                    <td>{e.note || "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
            {bid.engagements.length > 0 && (
              <tfoot>
                <tr>
                  <td colSpan={3}>
                    <b>Total</b>
                  </td>
                  <td className="num">
                    <b>{bid.total_engagement_days}</b>
                  </td>
                  <td className="num">
                    <b>{money(bid.total_convenience_bill)}</b>
                  </td>
                  <td></td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>

        <h3 className="subhead" style={{ marginTop: 20 }}>Cost lines</h3>
        <div className="tscroll">
          <table>
            <thead>
              <tr>
                <th className="num">#</th>
                <th>Description</th>
                <th>Date</th>
                <th>Reference</th>
                <th className="num">Amount</th>
                <th>Currency</th>
              </tr>
            </thead>
            <tbody>
              {bid.cost_lines.length === 0 ? (
                <tr>
                  <td colSpan={6} className="hint">
                    No cost lines recorded.
                  </td>
                </tr>
              ) : (
                bid.cost_lines.map((c) => (
                  <tr key={c.id}>
                    <td className="num">{c.line_number}</td>
                    <td>{c.description}</td>
                    <td className="num">{formatDMY(c.date)}</td>
                    <td>{c.reference || "—"}</td>
                    <td className="num">{money(c.amount)}</td>
                    <td>{c.currency}</td>
                  </tr>
                ))
              )}
            </tbody>
            {bid.cost_lines.length > 0 && (
              <tfoot>
                <tr>
                  <td colSpan={4}>
                    <b>Total</b>
                  </td>
                  <td className="num" colSpan={2}>
                    <b>{currencyPair(bid.total_cost_lines.BDT, bid.total_cost_lines.USD)}</b>
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>

        <div className="mgmt-cost-box">
          <span className="mgmt-cost-value">
            Management cost: {currencyPair(bid.management_cost.BDT, bid.management_cost.USD)}
          </span>
          <span className="mgmt-cost-formula">
            Cost lines ({currencyPair(bid.total_cost_lines.BDT, bid.total_cost_lines.USD)}) + convenience bill (৳
            {money(bid.total_convenience_bill)})
          </span>
        </div>
      </div>
    </div>
  );
}
