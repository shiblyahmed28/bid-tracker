export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export type BucketMode = "daily" | "monthly" | "quarterly";

/** The backend returns each bucket as a real date (TruncDate/TruncMonth/
 * TruncQuarter — quarter buckets are the quarter's first day), so quarter
 * numbers are derived here rather than trusting a pre-formatted string. */
export function formatBucketLabel(bucket: string, mode: BucketMode): string {
  const [y, m, d] = bucket.split("-").map(Number);
  if (mode === "daily") return `${String(d).padStart(2, "0")} ${MONTHS[m - 1]}`;
  if (mode === "monthly") return `${MONTHS[m - 1]} '${String(y).slice(2)}`;
  const quarter = Math.floor((m - 1) / 3) + 1;
  return `Q${quarter} '${String(y).slice(2)}`;
}
