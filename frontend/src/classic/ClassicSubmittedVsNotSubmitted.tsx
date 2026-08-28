import type { TrendPoint } from "../api/dashboard";
import { EmptyState, Skeleton } from "../dashboard/Skeleton";
import { formatBucketLabel, type BucketMode } from "../lib/bucketLabel";
import { GroupedBarChart } from "./GroupedBarChart";

interface ClassicSubmittedVsNotSubmittedProps {
  points: TrendPoint[] | null;
  bucketMode: BucketMode | null;
  loading: boolean;
}

export function ClassicSubmittedVsNotSubmitted({ points, bucketMode, loading }: ClassicSubmittedVsNotSubmittedProps) {
  return (
    <div className="card">
      <div className="chead">
        <h2>Submitted vs not submitted</h2>
        <div className="hgap" />
        <div className="rlegend">
          <span>
            <i style={{ background: "#4A9EE8" }} />
            Submitted
          </span>
          <span>
            <i style={{ background: "#E8506B" }} />
            Not submitted
          </span>
        </div>
      </div>
      <div className="cbody">
        {loading ? (
          <Skeleton height={180} />
        ) : !points || !bucketMode || points.every((p) => p.count === 0) ? (
          <EmptyState message="No submissions in this range" />
        ) : (
          <GroupedBarChart
            data={points.map((p) => ({
              label: formatBucketLabel(p.bucket, bucketMode),
              a: p.submitted,
              b: p.not_submitted,
            }))}
            width={600}
            height={180}
          />
        )}
      </div>
    </div>
  );
}
