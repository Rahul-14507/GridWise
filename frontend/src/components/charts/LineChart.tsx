import React from 'react';

export interface LineSeries {
  key: string;
  label: string;
  color: string;
  strokeDasharray?: string;
}

interface LineChartProps {
  data: Array<Record<string, any>>;
  series: LineSeries[];
  xAxisKey?: string;
  yAxisUnit?: string;
  height?: number;
  minY?: number;
  maxY?: number;
}

export const LineChart: React.FC<LineChartProps> = ({
  data,
  series,
  yAxisUnit = 'kW',
  height = 140,
  minY = 0,
  maxY,
}) => {
  if (data.length === 0) {
    return (
      <div className="chart-empty" style={{ height }}>
        <span className="text-xs text-muted">Awaiting real-time polling telemetry data...</span>
      </div>
    );
  }

  const width = 450;
  const padding = { top: 15, right: 15, bottom: 25, left: 35 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  // Compute scale boundaries
  let calculatedMax = maxY;
  if (calculatedMax === undefined) {
    calculatedMax = 0;
    for (const d of data) {
      for (const s of series) {
        const val = Number(d[s.key]) || 0;
        if (val > calculatedMax) calculatedMax = val;
      }
    }
    calculatedMax = Math.max(calculatedMax * 1.15, 10);
  }

  const getX = (index: number) => {
    if (data.length <= 1) return padding.left + innerWidth / 2;
    return padding.left + (index / (data.length - 1)) * innerWidth;
  };

  const getY = (value: number) => {
    const range = calculatedMax! - minY;
    const clamped = Math.max(minY, Math.min(calculatedMax!, value));
    const normalized = range > 0 ? (clamped - minY) / range : 0;
    return padding.top + innerHeight - normalized * innerHeight;
  };

  const buildPath = (s: LineSeries) => {
    return data
      .map((d, i) => {
        const val = Number(d[s.key]) || 0;
        const x = getX(i);
        const y = getY(val);
        return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(' ');
  };

  return (
    <div className="w-full">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible">
        {/* Y Axis Grid lines */}
        {[0, 0.5, 1.0].map((tickRatio, i) => {
          const val = minY + tickRatio * (calculatedMax! - minY);
          const y = padding.top + innerHeight - tickRatio * innerHeight;
          return (
            <g key={i}>
              <line
                x1={padding.left}
                y1={y}
                x2={width - padding.right}
                y2={y}
                stroke="currentColor"
                strokeOpacity="0.08"
                strokeDasharray="3 3"
              />
              <text
                x={padding.left - 4}
                y={y + 3}
                textAnchor="end"
                fontSize="9"
                fill="currentColor"
                fillOpacity="0.5"
                fontFamily="JetBrains Mono, monospace"
              >
                {val.toFixed(0)}{yAxisUnit}
              </text>
            </g>
          );
        })}

        {/* Data Lines */}
        {series.map((s) => (
          <path
            key={s.key}
            d={buildPath(s)}
            fill="none"
            stroke={s.color}
            strokeWidth="2"
            strokeDasharray={s.strokeDasharray}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))}

        {/* Latest Points */}
        {series.map((s) => {
          const lastIdx = data.length - 1;
          const lastVal = Number(data[lastIdx][s.key]) || 0;
          return (
            <circle
              key={`pt-${s.key}`}
              cx={getX(lastIdx)}
              cy={getY(lastVal)}
              r="3.5"
              fill={s.color}
              stroke="#ffffff"
              strokeWidth="1.5"
            />
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 justify-end text-[11px] mt-1">
        {series.map((s) => (
          <div key={s.key} className="flex items-center gap-1.5">
            <span
              className="inline-block w-3 h-0.5"
              style={{ backgroundColor: s.color }}
            />
            <span className="text-muted">{s.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
