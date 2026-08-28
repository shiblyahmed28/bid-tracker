import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import { todayISO } from "../lib/dateUtils";
import { DEFAULT_PRESET_INDEX, PRESETS } from "./presets";

interface DateRangeContextValue {
  from: string;
  to: string;
  presetIndex: number | null;
  setPreset: (index: number) => void;
  setCustomFrom: (value: string) => void;
  setCustomTo: (value: string) => void;
}

const DateRangeContext = createContext<DateRangeContextValue | undefined>(undefined);

/** The one shared control every dashboard panel reads from (§12). Scoped to
 * whichever page mounts <DateRangeProvider> — the executive dashboard here,
 * reusable by Classic view later since it's driven by the same control. */
export function DateRangeProvider({ children }: { children: ReactNode }) {
  const initial = useMemo(() => PRESETS[DEFAULT_PRESET_INDEX].range(todayISO()), []);
  const [from, setFrom] = useState(initial.from);
  const [to, setTo] = useState(initial.to);
  const [presetIndex, setPresetIndex] = useState<number | null>(DEFAULT_PRESET_INDEX);

  function setPreset(index: number) {
    const range = PRESETS[index].range(todayISO());
    setFrom(range.from);
    setTo(range.to);
    setPresetIndex(index);
  }

  function setCustomFrom(value: string) {
    setFrom(value);
    setPresetIndex(null);
  }

  function setCustomTo(value: string) {
    setTo(value);
    setPresetIndex(null);
  }

  return (
    <DateRangeContext.Provider value={{ from, to, presetIndex, setPreset, setCustomFrom, setCustomTo }}>
      {children}
    </DateRangeContext.Provider>
  );
}

export function useDateRange() {
  const ctx = useContext(DateRangeContext);
  if (!ctx) throw new Error("useDateRange must be used within a DateRangeProvider");
  return ctx;
}
