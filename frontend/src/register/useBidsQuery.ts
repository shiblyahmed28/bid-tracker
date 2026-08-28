import { useEffect, useRef, useState } from "react";

import { fetchBids, type BidListItem, type PaginatedResponse } from "../api/bids";
import { subscribeDataSynced } from "../lib/dataSyncBus";

interface UseBidsQueryParams {
  from: string;
  to: string;
  search: string;
  filters: Record<string, string>;
  page: number;
  pageSize: number;
}

export function useBidsQuery(params: UseBidsQueryParams) {
  const { from, to, search, filters, page, pageSize } = params;
  const filtersKey = JSON.stringify(filters);

  const [data, setData] = useState<PaginatedResponse<BidListItem> | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncVersion, setSyncVersion] = useState(0);
  const requestId = useRef(0);

  useEffect(() => subscribeDataSynced(() => setSyncVersion((v) => v + 1)), []);

  useEffect(() => {
    const id = ++requestId.current;
    setLoading(true);

    fetchBids({
      submission_after: from,
      submission_before: to,
      search: search || undefined,
      page,
      page_size: pageSize,
      ...filters,
    })
      .then((result) => {
        if (id !== requestId.current) return;
        setData(result);
        setLoading(false);
      })
      .catch(() => {
        if (id !== requestId.current) return;
        setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [from, to, search, filtersKey, page, pageSize, syncVersion]);

  return { data, loading };
}
