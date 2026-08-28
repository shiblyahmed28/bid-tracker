import { useEffect, useState } from "react";

import { fetchDistinctValues, type DistinctOption } from "../api/bids";
import { FILTERABLE_ENUM_COLUMNS } from "./columns";

type OptionsByField = Record<string, DistinctOption[]>;

/** Loaded once, lazily, the first time the filter panel (or a chip needing
 * a label lookup) actually needs them — unscoped by date range (§13's
 * dropdowns list every value that ever existed, not just ones in range). */
export function useEnumOptions(enabled: boolean) {
  const [options, setOptions] = useState<OptionsByField>({});
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!enabled || loaded) return;
    let cancelled = false;

    Promise.all(
      FILTERABLE_ENUM_COLUMNS.map((column) =>
        fetchDistinctValues(column.filterParam!).then((opts) => [column.filterParam!, opts] as const)
      )
    ).then((entries) => {
      if (cancelled) return;
      setOptions(Object.fromEntries(entries));
      setLoaded(true);
    });

    return () => {
      cancelled = true;
    };
  }, [enabled, loaded]);

  return options;
}
