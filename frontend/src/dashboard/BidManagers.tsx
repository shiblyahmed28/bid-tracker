import { fetchBreakdown } from "../api/dashboard";
import { EmptyState, Skeleton } from "./Skeleton";
import { useRangeQuery } from "./useRangeQuery";

const MAX_ROWS = 8;

export function BidManagers() {
  const { data, loading } = useRangeQuery((params) => fetchBreakdown({ ...params, by: "bid_manager" }));
  const rows = (data?.breakdown ?? []).slice(0, MAX_ROWS);

  return (
    <div className="card">
      <div className="chead">
        <h2>Bid managers</h2>
        <span className="scope">Selected range</span>
      </div>
      <div className="tscroll">
        {loading ? (
          <div style={{ padding: 15 }}>
            <Skeleton height={180} />
          </div>
        ) : rows.length === 0 ? (
          <EmptyState message="No bid managers in this range" />
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th style={{ textAlign: "right" }}>Bids</th>
                <th style={{ textAlign: "right" }}>Won</th>
                <th style={{ textAlign: "right" }}>Rate</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const rate = row.count ? Math.round((row.won / row.count) * 100) : 0;
                const tagClass = row.count && row.won / row.count >= 0.2 ? "t-won" : row.won === 0 ? "t-no" : "t-pend";
                return (
                  <tr key={row.label}>
                    <td className="trunc" style={{ maxWidth: 180 }}>
                      {row.label}
                    </td>
                    <td className="num" style={{ textAlign: "right" }}>
                      {row.count}
                    </td>
                    <td className="num" style={{ textAlign: "right" }}>
                      {row.won}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <span className={`tag ${tagClass}`}>{rate}%</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
