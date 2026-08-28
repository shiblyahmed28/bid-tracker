import { useDateRange } from "./DateRangeContext";
import { PRESETS } from "./presets";

interface RangeBarProps {
  matchedCount: number | null;
}

export function RangeBar({ matchedCount }: RangeBarProps) {
  const { from, to, presetIndex, setPreset, setCustomFrom, setCustomTo } = useDateRange();

  return (
    <div className="rangebar">
      <label htmlFor="range-from">Date range</label>
      <input id="range-from" type="date" value={from} onChange={(e) => setCustomFrom(e.target.value)} />
      <span style={{ color: "var(--muted)" }}>to</span>
      <input type="date" value={to} onChange={(e) => setCustomTo(e.target.value)} aria-label="Range end" />

      <div className="chips">
        {PRESETS.map((preset, index) => (
          <button
            key={preset.label}
            className={`chip${presetIndex === index ? " on" : ""}`}
            onClick={() => setPreset(index)}
          >
            {preset.label}
          </button>
        ))}
      </div>

      <div className="hgap" />
      <span className="rcount">
        {matchedCount === null ? (
          "Loading…"
        ) : (
          <>
            <b className="num">{matchedCount}</b> bids match this range
          </>
        )}
      </span>
    </div>
  );
}
