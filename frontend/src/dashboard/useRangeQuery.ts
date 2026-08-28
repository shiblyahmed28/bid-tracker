import { useEffect, useRef, useState } from "react";

import { useDateRange } from "./DateRangeContext";

interface RangeQueryResult<T> {
  data: T | null;
  loading: boolean;
  error: boolean;
}

/** Every panel re-fetches independently off the one shared range (§12) and
 * tracks its own loading/error state — this is what makes per-panel
 * skeletons possible instead of a single page-level spinner. A monotonic
 * request id discards any response that isn't from the latest request, so
 * rapidly switching presets can't let a slow, stale response clobber a
 * newer one. */
export function useRangeQuery<T>(
  fetcher: (params: { from: string; to: string }) => Promise<T>,
  extraDeps: unknown[] = []
): RangeQueryResult<T> {
  const { from, to } = useDateRange();
  const [state, setState] = useState<RangeQueryResult<T>>({ data: null, loading: true, error: false });
  const requestId = useRef(0);

  useEffect(() => {
    const id = ++requestId.current;
    setState((prev) => ({ ...prev, loading: true, error: false }));

    fetcher({ from, to })
      .then((data) => {
        if (id !== requestId.current) return;
        setState({ data, loading: false, error: false });
      })
      .catch(() => {
        if (id !== requestId.current) return;
        setState({ data: null, loading: false, error: true });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [from, to, ...extraDeps]);

  return state;
}
