import { fetchBreakdown } from "../api/dashboard";
import { EmptyState, Skeleton } from "./Skeleton";
import { useRangeQuery } from "./useRangeQuery";

export function TeamsBreakdown() {
  const { data, loading } = useRangeQuery((params) => fetchBreakdown({ ...params, by: "team" }));
  const rows = data?.breakdown ?? [];

  return (
    <div className="card">
      <div className="chead">
        <h2>Teams</h2>
        <span className="scope">New field · selected range</span>
      </div>
      <div className="tscroll">
        {loading ? (
          <div style={{ padding: 15 }}>
            <Skeleton height={140} />
          </div>
        ) : rows.length === 0 ? (
          <EmptyState message="No teams in this range" />
        ) : (
          <table>
            <thead>
              <tr>
                <th>Team</th>
                <th style={{ textAlign: "right" }}>Bids</th>
                <th style={{ textAlign: "right" }}>Won</th>
                <th style={{ textAlign: "right" }}>Lost</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.label}>
                  <td>
                    <b>{row.label}</b>
                  </td>
                  <td className="num" style={{ textAlign: "right" }}>
                    {row.count}
                  </td>
                  <td className="num" style={{ textAlign: "right" }}>
                    {row.won}
                  </td>
                  <td className="num" style={{ textAlign: "right" }}>
                    {row.lost}
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
