import { useEffect, useState } from "react";

import { fetchRegisterBreakdown, type RegisterBreakdownBy, type RegisterBreakdownRow } from "../api/bids";
import { EmptyState, Skeleton } from "../dashboard/Skeleton";

const MAX_ROWS = 8;

const PANELS: { by: RegisterBreakdownBy; title: string }[] = [
  { by: "client", title: "Clients" },
  { by: "team", title: "Teams" },
  { by: "bid_manager", title: "Bid managers" },
  { by: "submission_status", title: "Submission status" },
  { by: "result", title: "Result" },
];

interface BreakdownParams {
  submission_after: string;
  submission_before: string;
  search?: string;
  [filterParam: string]: string | number | undefined;
}

interface BreakdownPanelProps {
  by: RegisterBreakdownBy;
  title: string;
  params: BreakdownParams;
  scopeLabel: string;
}

function BreakdownPanel({ by, title, params, scopeLabel }: BreakdownPanelProps) {
  const [rows, setRows] = useState<RegisterBreakdownRow[] | null>(null);
  const paramsKey = JSON.stringify(params);

  useEffect(() => {
    setRows(null);
    fetchRegisterBreakdown({ ...params, by }).then((data) => setRows(data.breakdown));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [by, paramsKey]);

  const shown = (rows ?? []).slice(0, MAX_ROWS);
  const max = Math.max(...shown.map((r) => r.count), 1);

  return (
    <div className="card">
      <div className="chead">
        <h2>{title}</h2>
        <span className="scope">{scopeLabel}</span>
      </div>
      <div className="cbody">
        {rows === null ? (
          <Skeleton height={160} />
        ) : shown.length === 0 ? (
          <EmptyState message="No bids match these filters" />
        ) : (
          shown.map((row) => (
            <div className="lrow" key={row.label}>
              <span className="trunc" style={{ maxWidth: 190 }} title={row.label}>
                {row.label}
              </span>
              <div className="lbar">
                <i style={{ width: `${(row.count / max) * 100}%` }} />
              </div>
              <b className="num">{row.count}</b>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

interface RegisterBreakdownChartsProps {
  params: BreakdownParams;
  filterSummary: string;
}

/** §13/§18 Phase 18 item 5 — breaks down the register's currently filtered
 * set (every active filter and search, not only the shared date range) by
 * client, team, bid manager, submission status and result. */
export function RegisterBreakdownCharts({ params, filterSummary }: RegisterBreakdownChartsProps) {
  return (
    <div className="grid c2">
      {PANELS.map((panel) => (
        <BreakdownPanel key={panel.by} by={panel.by} title={panel.title} params={params} scopeLabel={filterSummary} />
      ))}
    </div>
  );
}
