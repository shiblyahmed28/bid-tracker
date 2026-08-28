import { shiftISO, todayISO } from "../lib/dateUtils";

export interface RangePreset {
  label: string;
  range: (today: string) => { from: string; to: string };
}

/** §12: only the default (±7 days) is symmetric around today — 30/90 days
 * and 12 months are trailing windows ending today, matching the mockup. */
export const PRESETS: RangePreset[] = [
  { label: "±7 days", range: (today) => ({ from: shiftISO(today, -7), to: shiftISO(today, 7) }) },
  { label: "30 days", range: (today) => ({ from: shiftISO(today, -30), to: today }) },
  { label: "90 days", range: (today) => ({ from: shiftISO(today, -90), to: today }) },
  {
    label: "This year",
    range: () => {
      const year = new Date(`${todayISO()}T00:00:00`).getFullYear();
      return { from: `${year}-01-01`, to: `${year}-12-31` };
    },
  },
  { label: "12 months", range: (today) => ({ from: shiftISO(today, -365), to: today }) },
  // "All" has no real unbounded query support — 2000-2100 is the same valid
  // year window the backend itself enforces on every stored date (§8), so
  // it's guaranteed to include everything without a special "no bound" case.
  { label: "All", range: () => ({ from: "2000-01-01", to: "2100-12-31" }) },
];

export const DEFAULT_PRESET_INDEX = 0;
