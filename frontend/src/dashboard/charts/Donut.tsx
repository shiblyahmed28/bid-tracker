export interface DonutSlice {
  key: string;
  value: number;
  color: string;
}

interface DonutProps {
  slices: DonutSlice[];
  size?: number;
  centerLabel?: string;
}

export function Donut({ slices, size = 148, centerLabel = "BIDS" }: DonutProps) {
  const total = slices.reduce((sum, slice) => sum + slice.value, 0);
  const denominator = total || 1;
  const c = size / 2;
  const r = size / 2 - 5;
  const ir = r * 0.62;

  let angle = -Math.PI / 2;
  const point = (radius: number, a: number): [number, number] => [
    c + radius * Math.cos(a),
    c + radius * Math.sin(a),
  ];

  const paths = slices
    .filter((slice) => slice.value > 0)
    .map((slice) => {
      const a0 = angle;
      const a1 = a0 + (2 * Math.PI * slice.value) / denominator;
      const largeArc = a1 - a0 > Math.PI ? 1 : 0;
      const [x1, y1] = point(r, a0);
      const [x2, y2] = point(r, a1);
      const [x3, y3] = point(ir, a1);
      const [x4, y4] = point(ir, a0);
      angle = a1;
      return (
        <path
          key={slice.key}
          d={`M${x1} ${y1}A${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}L${x3} ${y3}A${ir} ${ir} 0 ${largeArc} 0 ${x4} ${y4}Z`}
          fill={slice.color}
        >
          <title>
            {slice.key}: {slice.value}
          </title>
        </path>
      );
    });

  return (
    <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
      {paths}
      <text x={c} y={c - 1} textAnchor="middle" fontSize="20" fontWeight="700" fill="#2E2E38" fontFamily="var(--mono)">
        {total}
      </text>
      <text x={c} y={c + 13} textAnchor="middle" fontSize="8.5" fill="#82887F" letterSpacing="1">
        {centerLabel}
      </text>
    </svg>
  );
}
