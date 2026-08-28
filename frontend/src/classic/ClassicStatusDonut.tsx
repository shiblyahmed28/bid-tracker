import type { DashboardSummary } from "../api/dashboard";
import { Donut } from "../dashboard/charts/Donut";
import { EmptyState, Skeleton } from "../dashboard/Skeleton";
import { classicStatusSlices } from "./classicGrouping";

export function ClassicStatusDonut({ summary, loading }: { summary: DashboardSummary | null; loading: boolean }) {
  const slices = summary ? classicStatusSlices(summary) : [];
  const total = slices.reduce((sum, slice) => sum + slice.value, 0);

  return (
    <div className="card">
      <div className="chead">
        <h2>Bid status breakdown</h2>
      </div>
      <div className="cbody dwrap">
        {loading ? (
          <Skeleton height={148} width={148} />
        ) : total === 0 ? (
          <EmptyState message="No bids in this range" />
        ) : (
          <>
            <Donut slices={slices} size={148} />
            <ul className="dleg">
              {slices.map((slice) => (
                <li key={slice.key}>
                  <i style={{ background: slice.color, borderRadius: "50%" }} />
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
