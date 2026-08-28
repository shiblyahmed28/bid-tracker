import { fetchBreakdown } from "../api/dashboard";
import { EmptyState, Skeleton } from "../dashboard/Skeleton";
import { useRangeQuery } from "../dashboard/useRangeQuery";

const MAX_ROWS = 6;

export function ClassicClientSummary() {
  const { data, loading } = useRangeQuery((params) => fetchBreakdown({ ...params, by: "client" }));
  const rows = (data?.breakdown ?? []).slice(0, MAX_ROWS);
  const max = Math.max(...rows.map((r) => r.count), 1);

  return (
    <div className="card">
      <div className="chead">
        <h2>Summary by client</h2>
      </div>
      <div className="cbody">
        {loading ? (
          <Skeleton height={140} />
        ) : rows.length === 0 ? (
          <EmptyState message="No clients in this range" />
        ) : (
          rows.map((row) => (
            <div className="lrow" key={row.label}>
              <span className="trunc" style={{ maxWidth: 230 }} title={row.label}>
                {row.label}
              </span>
              <div className="lbar">
                <i style={{ width: `${(row.count / max) * 100}%`, background: "#B9B0F0" }} />
                <u style={{ width: `${(row.won / max) * 100}%`, background: "#6C63FF" }} />
              </div>
              <b className="num">{row.count}</b>
              <small className="num" style={{ color: "#6C63FF" }}>
                {row.won}W
              </small>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
