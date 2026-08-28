import { fetchBids } from "../api/bids";
import { fetchClassicSummary, fetchTrend } from "../api/dashboard";
import { ClassicClientSummary } from "../classic/ClassicClientSummary";
import { ClassicStatusDonut } from "../classic/ClassicStatusDonut";
import { ClassicSubmittedVsNotSubmitted } from "../classic/ClassicSubmittedVsNotSubmitted";
import { ClassicTable } from "../classic/ClassicTable";
import { DateRangeProvider } from "../dashboard/DateRangeContext";
import { RangeBar } from "../dashboard/RangeBar";
import { useRangeQuery } from "../dashboard/useRangeQuery";

function ClassicContent() {
  const { data: summary, loading: summaryLoading } = useRangeQuery(fetchClassicSummary);
  const { data: trend, loading: trendLoading } = useRangeQuery(fetchTrend);
  const { data: bidsPage, loading: bidsLoading } = useRangeQuery((params) =>
    fetchBids({
      submission_after: params.from,
      submission_before: params.to,
      page: 1,
      page_size: 25,
    })
  );

  return (
    <>
      <div className="banner b-info">
        The <b>Classic view</b> — the original layout, rebuilt so it renders. Same columns and charts, now
        driven by the shared date range.
      </div>

      <RangeBar matchedCount={summary?.total ?? null} />

      <ClassicTable rows={bidsPage?.results ?? null} totalCount={bidsPage?.count ?? null} loading={bidsLoading} />

      <div className="grid c2">
        <ClassicStatusDonut summary={summary} loading={summaryLoading} />
        <ClassicSubmittedVsNotSubmitted
          points={trend?.points ?? null}
          bucketMode={trend?.bucket ?? null}
          loading={trendLoading}
        />
      </div>

      <ClassicClientSummary />
    </>
  );
}

export function ClassicPage() {
  return (
    <div className="classic-scope">
      <DateRangeProvider>
        <ClassicContent />
      </DateRangeProvider>
    </div>
  );
}
