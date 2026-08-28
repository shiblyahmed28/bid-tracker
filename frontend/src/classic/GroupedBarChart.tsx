export interface GroupedBarDatum {
  label: string;
  a: number;
  b: number;
}

interface GroupedBarChartProps {
  data: GroupedBarDatum[];
  width?: number;
  height?: number;
}

/** Two side-by-side bars per bucket (not stacked) — Classic view's
 * "Submitted vs not submitted" panel, matching the mockup's non-stacked
 * bars() branch with the same blue/pink pair. */
export function GroupedBarChart({ data, width = 600, height = 180 }: GroupedBarChartProps) {
  const pad = { t: 12, r: 8, b: 24, l: 32 };
  const iw = width - pad.l - pad.r;
  const ih = height - pad.t - pad.b;
  const max = Math.max(...data.map((d) => Math.max(d.a, d.b)), 1);
  const gap = iw / Math.max(data.length, 1);
  const barWidth = Math.max(gap * 0.3, 2);
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
        return (
          <g key={`${d.label}-${i}`}>
            <rect x={x - barWidth - 1} y={pad.t + ih - (ih * d.a) / max} width={barWidth} height={(ih * d.a) / max} fill="#4A9EE8" rx={2}>
              <title>
                {d.label}: {d.a}
              </title>
            </rect>
            <rect x={x + 1} y={pad.t + ih - (ih * d.b) / max} width={barWidth} height={(ih * d.b) / max} fill="#E8506B" rx={2}>
              <title>
                {d.label}: {d.b}
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
