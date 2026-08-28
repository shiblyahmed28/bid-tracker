export interface StackedBarDatum {
  label: string;
  a: number;
  b: number;
}

interface StackedBarChartProps {
  data: StackedBarDatum[];
  width?: number;
  height?: number;
}

/** Submitted (a, deep green) stacked on not-submitted (b, grey) — used by
 * both the "Submitted vs not submitted" panel and the runway's fallback for
 * spans too long for a day rail (§12), same as the mockup reuses one chart
 * for both. */
export function StackedBarChart({ data, width = 620, height = 180 }: StackedBarChartProps) {
  const pad = { t: 12, r: 8, b: 24, l: 32 };
  const iw = width - pad.l - pad.r;
  const ih = height - pad.t - pad.b;
  const max = Math.max(...data.map((d) => d.a + d.b), 1);
  const gap = iw / Math.max(data.length, 1);
  const barWidth = Math.max(gap * 0.6, 2);
  const step = Math.max(1, Math.ceil(data.length / 12));

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} preserveAspectRatio="xMidYMid meet">
      {[0, 1, 2, 3, 4].map((i) => {
        const y = pad.t + ih - (ih * i) / 4;
        return (
          <g key={i}>
            <line x1={pad.l} y1={y} x2={width - pad.r} y2={y} stroke="#EFF2ED" />
            <text x={pad.l - 5} y={y + 3.5} textAnchor="end" fontSize="9" fill="#82887F">
              {Math.round((max * i) / 4)}
            </text>
          </g>
        );
      })}
      {data.map((d, i) => {
        const x = pad.l + gap * i + gap / 2;
        const ha = (ih * d.a) / max;
        const hb = (ih * d.b) / max;
        return (
          <g key={`${d.label}-${i}`}>
            <rect x={x - barWidth / 2} y={pad.t + ih - ha - hb} width={barWidth} height={hb} fill="#D6DCD2" rx={2}>
              <title>
                {d.label}: {d.b} not submitted
              </title>
            </rect>
            <rect x={x - barWidth / 2} y={pad.t + ih - ha} width={barWidth} height={ha} fill="#2E6130" rx={2}>
              <title>
                {d.label}: {d.a} submitted
              </title>
            </rect>
            {i % step === 0 && (
              <text x={x} y={height - 7} textAnchor="middle" fontSize="8.5" fill="#82887F">
                {d.label}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
