import tr from "../i18n";

const CHART_COLORS = ["#C65D3A", "#3B82F6", "#8B5CF6", "#10B981", "#F59E0B"];

function getPoint(monthIndex, value, maxValue, width, height, padding) {
  const stepX = (width - padding * 2) / 2;
  const chartHeight = height - padding * 2;
  const normalized = maxValue > 0 ? value / maxValue : 0;
  const x = padding + monthIndex * stepX;
  const y = height - padding - normalized * chartHeight;
  return { x, y };
}

export default function TrendLineChart({ series }) {
  const width = 600;
  const height = 250;
  const padding = 32;
  const visibleSeries = series.slice(0, 5);
  const maxValue = Math.max(
    ...visibleSeries.flatMap((item) => [item.jan_factor, item.feb_factor, item.mar_factor]),
    0
  ) + 0.5;
  const labels = [tr.monthJanuary, tr.monthFebruary, tr.monthMarch];

  if (!visibleSeries.length) {
    return (
      <article className="glass-card trend-card">
        <h3>{tr.trendChartTitle}</h3>
        <p className="trend-empty">{tr.noTrendChart}</p>
      </article>
    );
  }

  return (
    <article className="glass-card trend-card">
      <h3>{tr.trendChartTitle}</h3>
      <svg viewBox={`0 0 ${width} ${height}`} className="trend-chart" role="img">
        <line
          x1={padding}
          y1={height - padding}
          x2={width - padding}
          y2={height - padding}
          className="chart-axis"
        />
        <line
          x1={padding}
          y1={padding}
          x2={padding}
          y2={height - padding}
          className="chart-axis"
        />

        {labels.map((label, index) => {
          const point = getPoint(index, 0, maxValue, width, height, padding);
          return (
            <text
              key={label}
              x={point.x}
              y={height - 8}
              textAnchor="middle"
              className="chart-label"
            >
              {label}
            </text>
          );
        })}

        {visibleSeries.map((item, index) => {
          const points = [item.jan_factor, item.feb_factor, item.mar_factor].map(
            (value, monthIndex) =>
              getPoint(monthIndex, value, maxValue, width, height, padding)
          );
          const path = points.map((point) => `${point.x},${point.y}`).join(" ");
          const color = CHART_COLORS[index % CHART_COLORS.length];

          return (
            <g key={item.key}>
              <polyline fill="none" stroke={color} strokeWidth="3" points={path} />
              {points.map((point, pointIndex) => (
                <circle
                  key={`${item.key}-${pointIndex}`}
                  cx={point.x}
                  cy={point.y}
                  r="4.5"
                  fill={color}
                >
                  <title>
                    {item.label} - {labels[pointIndex]}:{" "}
                    {Number(
                      [item.jan_factor, item.feb_factor, item.mar_factor][pointIndex]
                    ).toFixed(2)}
                    x
                  </title>
                </circle>
              ))}
            </g>
          );
        })}
      </svg>

      <div className="chart-legend">
        {visibleSeries.map((item, index) => (
          <span key={item.key} className="chart-legend-item">
            <i style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }} />
            {item.label}
          </span>
        ))}
      </div>
    </article>
  );
}
