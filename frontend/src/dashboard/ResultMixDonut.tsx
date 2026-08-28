import type { DashboardSummary } from "../api/dashboard";
import { Donut } from "./charts/Donut";
import { groupResultBreakdown } from "./resultGrouping";
import { EmptyState, Skeleton } from "./Skeleton";

interface ResultMixDonutProps {
  summary: DashboardSummary | null;
  loading: boolean;
}

export function ResultMixDonut({ summary, loading }: ResultMixDonutProps) {
  const slices = summary ? groupResultBreakdown(summary.result_breakdown) : [];
  const total = slices.reduce((sum, slice) => sum + slice.value, 0);

  return (
    <div className="card">
      <div className="chead">
        <h2>Result mix</h2>
        <span className="scope">Selected range</span>
      </div>
      <div className="cbody dwrap">
        {loading ? (
          <Skeleton height={148} width={148} />
        ) : total === 0 ? (
          <EmptyState message="No results in this range" />
        ) : (
          <>
            <Donut slices={slices} size={148} />
            <ul className="dleg">
              {slices.map((slice) => (
                <li key={slice.key}>
                  <i style={{ background: slice.color }} />
                  {slice.key}
                  <b className="num">{slice.value}</b>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
