import { fetchBgExposure, fetchSummary, fetchTrend } from "../api/dashboard";
import { BidManagers } from "../dashboard/BidManagers";
import { ClientsByVolume } from "../dashboard/ClientsByVolume";
import { DashboardBidTable } from "../dashboard/DashboardBidTable";
import { DateRangeProvider } from "../dashboard/DateRangeContext";
import { KpiCards } from "../dashboard/KpiCards";
import { RangeBar } from "../dashboard/RangeBar";
import { ResultMixDonut } from "../dashboard/ResultMixDonut";
import { SecurityExpiring } from "../dashboard/SecurityExpiring";
import { SubmissionRunway } from "../dashboard/SubmissionRunway";
import { SubmittedVsNotSubmitted } from "../dashboard/SubmittedVsNotSubmitted";
import { TeamsBreakdown } from "../dashboard/TeamsBreakdown";
import { useRangeQuery } from "../dashboard/useRangeQuery";

const BG_EXPOSURE_DAYS = 60;

function DashboardContent() {
  const { data: summary, loading: summaryLoading } = useRangeQuery(fetchSummary);
  const { data: trend, loading: trendLoading } = useRangeQuery(fetchTrend);
  const { data: bgExposure, loading: bgExposureLoading } = useRangeQuery((params) =>
    fetchBgExposure({ ...params, days: BG_EXPOSURE_DAYS })
  );

  return (
    <>
      <RangeBar matchedCount={summary?.total ?? null} />

      <SubmissionRunway
        trendPoints={trend?.points ?? null}
        trendBucketMode={trend?.bucket ?? null}
        trendLoading={trendLoading}
      />

      <KpiCards summary={summary} loading={summaryLoading} bgExposureCount={bgExposure?.count ?? null} />

      <div className="grid c2">
        <SubmittedVsNotSubmitted points={trend?.points ?? null} bucketMode={trend?.bucket ?? null} loading={trendLoading} />
        <ResultMixDonut summary={summary} loading={summaryLoading} />
      </div>

      <div className="grid c2">
        <ClientsByVolume />
        <BidManagers />
      </div>

      <div className="grid c2">
        <TeamsBreakdown />
        <SecurityExpiring data={bgExposure} loading={bgExposureLoading} />
      </div>

      <DashboardBidTable />
    </>
  );
}

export function DashboardPage() {
  return (
    <DateRangeProvider>
      <DashboardContent />
    </DateRangeProvider>
  );
}
