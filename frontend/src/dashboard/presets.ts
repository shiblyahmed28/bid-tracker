import { shiftISO, todayISO } from "../lib/dateUtils";

export interface RangePreset {
  label: string;
  range: (today: string) => { from: string; to: string };
}

/** §12 Phase 18 item 3: the first three presets are symmetric around today —
 * each label spells out the total span (e.g. "±7 days (14 days)") so it's
 * unambiguous that ±7 means 14 days end to end, not 7. */
export const PRESETS: RangePreset[] = [
  { label: "±7 days (14 days)", range: (today) => ({ from: shiftISO(today, -7), to: shiftISO(today, 7) }) },
  { label: "±14 days (28 days)", range: (today) => ({ from: shiftISO(today, -14), to: shiftISO(today, 14) }) },
  { label: "±30 days (60 days)", range: (today) => ({ from: shiftISO(today, -30), to: shiftISO(today, 30) }) },
  {
    label: "This year",
    range: () => {
      const year = new Date(`${todayISO()}T00:00:00`).getFullYear();
      return { from: `${year}-01-01`, to: `${year}-12-31` };
    },
  },
  { label: "Past 12 months", range: (today) => ({ from: shiftISO(today, -365), to: today }) },
  // "All" has no real unbounded query support — 2000-2100 is the same valid
  // year window the backend itself enforces on every stored date (§8), so
  // it's guaranteed to include everything without a special "no bound" case.
  { label: "All", range: () => ({ from: "2000-01-01", to: "2100-12-31" }) },
];

export const DEFAULT_PRESET_INDEX = 0;
