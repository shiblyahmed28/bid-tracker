import type { DonutSlice } from "./charts/Donut";

/** Mirrors the mockup's result-mix grouping: Lowest counts with Won, Short
 * Listed with Qualified, Disqualified with Lost. Any real-sheet value the
 * mockup's synthetic data never had (Un-opened, Information Not Available,
 * Tie, truly blank) falls into "Not recorded" rather than being dropped. */
const KNOWN_KEYS = new Set([
  "PENDING",
  "WON",
  "LOWEST",
  "LOST",
  "DISQUALIFIED",
  "QUALIFIED",
  "SHORT LISTED",
  "CANCELLED",
]);

export function groupResultBreakdown(breakdown: Record<string, number>): DonutSlice[] {
  const get = (key: string) => breakdown[key] ?? 0;
  const notRecorded = Object.entries(breakdown).reduce(
    (sum, [key, value]) => (KNOWN_KEYS.has(key) ? sum : sum + value),
    0
  );

  return [
    { key: "Pending", value: get("PENDING"), color: "#D89B2C" },
    { key: "Won / Lowest", value: get("WON") + get("LOWEST"), color: "#2E6130" },
    { key: "Lost", value: get("LOST") + get("DISQUALIFIED"), color: "#C4453A" },
    { key: "Qualified", value: get("QUALIFIED") + get("SHORT LISTED"), color: "#8FC157" },
    { key: "Cancelled", value: get("CANCELLED"), color: "#A9AFA4" },
    { key: "Not recorded", value: notRecorded, color: "#DDE2D8" },
  ];
}
