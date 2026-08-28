import type { DashboardSummary } from "../api/dashboard";
import type { DonutSlice } from "../dashboard/charts/Donut";

const KNOWN_RESULT_KEYS = new Set([
  "PENDING",
  "WON",
  "LOWEST",
  "LOST",
  "DISQUALIFIED",
  "QUALIFIED",
  "SHORT LISTED",
  "CANCELLED",
]);

/** The Classic view's own 6-category status donut (§13/mockup vClassic) —
 * a different grouping from the main dashboard's result-only mix, since it
 * blends submission_status (Bid Submitted / Not Submitted) with result. */
export function classicStatusSlices(summary: DashboardSummary): DonutSlice[] {
  const rb = summary.result_breakdown;
  const get = (key: string) => rb[key] ?? 0;
  const unknown = Object.entries(rb).reduce(
    (sum, [key, value]) => (KNOWN_RESULT_KEYS.has(key) ? sum : sum + value),
    0
  );

  return [
    { key: "Bid Submitted", value: summary.submitted, color: "#4A9EE8" },
    { key: "Not Submitted", value: summary.not_submitted, color: "#2FBF71" },
    { key: "Won", value: get("WON") + get("LOWEST"), color: "#F5A623" },
    { key: "Lost", value: get("LOST"), color: "#E8506B" },
    { key: "Result Pending", value: get("PENDING"), color: "#8B7BE8" },
    { key: "Unknown", value: unknown, color: "#3B7FD4" },
  ];
}
