import type { TrendPoint } from "../api/dashboard";
import { formatBucketLabel, type BucketMode } from "../lib/bucketLabel";
import { StackedBarChart } from "./charts/StackedBarChart";
import { EmptyState, Skeleton } from "./Skeleton";

interface SubmittedVsNotSubmittedProps {
  points: TrendPoint[] | null;
  bucketMode: BucketMode | null;
  loading: boolean;
}

export function SubmittedVsNotSubmitted({ points, bucketMode, loading }: SubmittedVsNotSubmittedProps) {
  return (
    <div className="card">
      <div className="chead">
        <h2>Submitted vs not submitted</h2>
        <span className="scope">Selected range</span>
        <div className="hgap" />
        <div className="rlegend">
          <span>
            <i style={{ background: "var(--deep)" }} />
            Submitted
          </span>
          <span>
            <i style={{ background: "#D6DCD2" }} />
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
          <StackedBarChart
            data={points.map((p) => ({ label: formatBucketLabel(p.bucket, bucketMode), a: p.submitted, b: p.not_submitted }))}
            width={620}
            height={180}
          />
        )}
      </div>
    </div>
  );
}
