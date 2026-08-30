import { useState } from "react";

import { BidTable } from "../register/BidTable";
import { COLUMNS } from "../register/columns";
import { Pager } from "../register/Pager";
import { useBidsQuery } from "../register/useBidsQuery";
import { useDateRange } from "./DateRangeContext";

const DEFAULT_PAGE_SIZE = 25;

// §12/§18 Phase 18 item 4: the dashboard's own read-only bid table — same
// shared date range as every other panel, newest first, server-paginated.
const DASHBOARD_TABLE_KEYS = [
  "serial",
  "client",
  "team",
  "stage",
  "bid_manager",
  "engaged_resources",
  "published_date",
  "submission_date",
  "submission_status",
  "result",
];

const DASHBOARD_TABLE_COLUMNS = DASHBOARD_TABLE_KEYS.map((key) => COLUMNS.find((c) => c.key === key)!);

export function DashboardBidTable() {
  const { from, to } = useDateRange();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);

  const { data, loading } = useBidsQuery({ from, to, search: "", filters: {}, page, pageSize });

  return (
    <div className="card">
      <div className="chead">
        <h2>Bids in range</h2>
        <span className="scope">Selected range · newest first</span>
      </div>
      <BidTable columns={DASHBOARD_TABLE_COLUMNS} rows={data?.results ?? []} loading={loading} />
      {!loading && (
        <Pager
          page={page}
          pageSize={pageSize}
          total={data?.count ?? 0}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPageSize(size);
            setPage(1);
          }}
        />
      )}
    </div>
  );
}
