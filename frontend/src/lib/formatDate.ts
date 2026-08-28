/** §2.7: store UTC, render Dhaka — every timestamp in the UI goes through
 * this rather than the viewer's local timezone. */
const DHAKA_TZ = "Asia/Dhaka";

export function formatSyncTime(isoString: string | null | undefined): string | null {
  if (!isoString) return null;
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: DHAKA_TZ,
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(isoString));
}
