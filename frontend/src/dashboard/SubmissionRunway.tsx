import { useNavigate } from "react-router-dom";

import { fetchDeadlines, type DeadlineItem, type TrendPoint } from "../api/dashboard";
import { formatBucketLabel, MONTHS, type BucketMode } from "../lib/bucketLabel";
import { daysBetween, formatDMY, shiftISO, todayISO } from "../lib/dateUtils";
import { StackedBarChart } from "./charts/StackedBarChart";
import { useDateRange } from "./DateRangeContext";
import { Skeleton } from "./Skeleton";
import { useRangeQuery } from "./useRangeQuery";

const MARKER_CLASS: Record<DeadlineItem["marker"], string> = {
  submitted: "ok",
  open: "open",
  passed: "bad",
};

const RAIL_MAX_DAYS = 31;

interface SubmissionRunwayProps {
  trendPoints: TrendPoint[] | null;
  trendBucketMode: BucketMode | null;
  trendLoading: boolean;
}

/** The signature panel (§12). ≤31-day spans get a day-by-day rail with
 * clickable stage markers; longer spans fall back to the same bucketed
 * stacked-volume chart the "Submitted vs not submitted" panel uses. */
export function SubmissionRunway({ trendPoints, trendBucketMode, trendLoading }: SubmissionRunwayProps) {
  const { from, to } = useDateRange();
  const span = daysBetween(from, to);
  const today = todayISO();
  const useRail = span <= RAIL_MAX_DAYS;

  const { data: deadlines, loading: railLoading } = useRangeQuery(fetchDeadlines, [useRail]);
  const loading = useRail ? railLoading : trendLoading;

  const railItems = useRail && deadlines?.mode === "rail" ? deadlines.items : [];
  const hasFutureBids = useRail
    ? railItems.some((item) => item.submission_date > today)
    : (trendPoints ?? []).some((point) => point.bucket > today && point.count > 0);

  return (
    <div className="card">
      <div className="chead">
        <h2>Submission runway</h2>
        <span className="scope">
          {formatDMY(from)} → {formatDMY(to)}
        </span>
        <div className="hgap" />
        <div className="rlegend">
          <span>
            <i style={{ background: "var(--deep)" }} />
            Submitted
          </span>
          <span>
            <i style={{ background: "var(--warn)" }} />
            Open
          </span>
          <span>
            <i style={{ background: "var(--danger)" }} />
            Passed, not submitted
          </span>
        </div>
      </div>
      <div className="cbody" style={{ padding: "16px 14px 8px" }}>
        {loading ? (
          <Skeleton height={104} />
        ) : useRail ? (
          <DayRail from={from} span={span} today={today} items={railItems} />
        ) : (
          <div>
            {trendPoints && trendBucketMode && (
              <StackedBarChart
                data={trendPoints.map((p) => ({
                  label: formatBucketLabel(p.bucket, trendBucketMode),
                  a: p.submitted,
                  b: p.not_submitted,
                }))}
                width={880}
                height={150}
              />
            )}
            <p className="hint" style={{ textAlign: "center" }}>
              Range spans {span > 9000 ? "all data" : `${span} days`} — showing bucketed volume instead of a
              day-by-day rail.
            </p>
          </div>
        )}
        {!loading && !hasFutureBids && (
          <div className="rnote">
            <strong>Nothing scheduled after today.</strong> Every row in the sheet was entered after its
            submission date had passed, so the 7-day deadline alert has nothing to fire on. Enter tenders when
            they are published and this rail fills up.
          </div>
        )}
      </div>
    </div>
  );
}

function DayRail({ from, span, today, items }: { from: string; span: number; today: string; items: DeadlineItem[] }) {
  const navigate = useNavigate();

  const byDay = new Map<string, DeadlineItem[]>();
  for (const item of items) {
    const list = byDay.get(item.submission_date) ?? [];
    list.push(item);
    byDay.set(item.submission_date, list);
  }

  const days = Array.from({ length: span + 1 }, (_, i) => shiftISO(from, i));

  return (
    <div className="rail">
      <div className="railline" />
      {days.map((day) => {
        const hits = byDay.get(day) ?? [];
        const isToday = day === today;
        const [, m, d] = day.split("-");

        return (
          <div className={`rday${isToday ? " today" : ""}`} key={day}>
            <div className="rmarks">
              {hits.slice(0, 4).map((hit) => (
                <button
                  key={hit.id}
                  className={`rmark ${MARKER_CLASS[hit.marker]}`}
                  onClick={() => navigate(`/bids/${hit.id}`)}
                  title={`${hit.client} — ${hit.stage}`}
                >
                  {(hit.stage || "").slice(0, 6)}
                </button>
              ))}
              {hits.length > 4 && <span className="mini">+{hits.length - 4}</span>}
            </div>
            <div className={`rtick${isToday ? " t" : ""}`} />
            <div className="rlab">
              <b className="num">{Number(d)}</b>
              <span>{MONTHS[Number(m) - 1]}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
