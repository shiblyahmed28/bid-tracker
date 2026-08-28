import { fetchBreakdown } from "../api/dashboard";
import { EmptyState, Skeleton } from "./Skeleton";
import { useRangeQuery } from "./useRangeQuery";

const MAX_ROWS = 8;

export function ClientsByVolume() {
  const { data, loading } = useRangeQuery((params) => fetchBreakdown({ ...params, by: "client" }));
  const rows = (data?.breakdown ?? []).slice(0, MAX_ROWS);
  const max = Math.max(...rows.map((r) => r.count), 1);

  return (
    <div className="card">
      <div className="chead">
        <h2>Clients by volume</h2>
        <span className="scope">Selected range</span>
      </div>
      <div className="cbody">
        {loading ? (
          <Skeleton height={180} />
        ) : rows.length === 0 ? (
          <EmptyState message="No clients in this range" />
        ) : (
          <>
            {rows.map((row) => (
              <div className="lrow" key={row.label}>
                <span className="trunc" style={{ maxWidth: 190 }} title={row.label}>
                  {row.label}
                </span>
                <div className="lbar">
                  <i style={{ width: `${(row.count / max) * 100}%` }} />
                  <u style={{ width: `${(row.won / max) * 100}%` }} />
                </div>
                <b className="num">{row.count}</b>
                <small className="num">{row.won}W</small>
              </div>
            ))}
            <p className="lfoot">
              <i style={{ background: "#CBD6C4" }} />
              Bids <i style={{ background: "var(--deep)" }} />
              Won
            </p>
          </>
        )}
      </div>
    </div>
  );
}
