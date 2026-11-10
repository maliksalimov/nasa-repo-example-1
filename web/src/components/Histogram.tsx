import { useMemo } from 'react'
import { bin, max } from 'd3-array'
import { scaleLinear } from 'd3-scale'
import { formatMetric } from '../format'
import type { MetricBaseline, MetricKey } from '../types'
import { useWidth } from '../useWidth'

const M = { top: 8, right: 8, bottom: 26, left: 8 }

/**
 * Distribution of one metric. The shaded band is the normal range (Q1-Q3),
 * the solid line is the median, ticks under the axis are this week's values.
 */
export function Histogram({ metric, stats, recent }: { metric: MetricKey; stats: MetricBaseline; recent: number[] }) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(320)
  const height = 150

  const { x, bins, y } = useMemo(() => {
    const hi = Math.max(stats.max, ...recent)
    const x = scaleLinear().domain([0, hi]).nice().range([M.left, width - M.right])
    const bins = bin().domain(x.domain() as [number, number]).thresholds(x.ticks(24))(stats.values)
    const y = scaleLinear().domain([0, max(bins, (b) => b.length) ?? 1]).range([height - M.bottom - 8, M.top])
    return { x, bins, y }
  }, [stats, recent, width])

  const base = height - M.bottom - 8
  const ticks = x.ticks(width < 360 ? 3 : 4)

  return (
    <div ref={wrapRef}>
      <svg
        width={width}
        height={height}
        role="img"
        aria-label={`Normal aralıq ${formatMetric(metric, stats.q1)} ilə ${formatMetric(metric, stats.q3)} arası, median ${formatMetric(metric, stats.median)}`}
      >
        <rect className="iqr-band" x={x(stats.q1)} width={x(stats.q3) - x(stats.q1)} y={M.top} height={base - M.top} />
        {bins.map((b, i) => (
          <rect
            key={i}
            className="bar"
            x={x(b.x0 ?? 0) + 0.5}
            width={Math.max(0, x(b.x1 ?? 0) - x(b.x0 ?? 0) - 1)}
            y={y(b.length)}
            height={base - y(b.length)}
          />
        ))}
        <line className="median-line" x1={x(stats.median)} x2={x(stats.median)} y1={M.top - 4} y2={base} />
        {recent.map((value, i) => (
          <line key={i} className="rug" x1={x(value)} x2={x(value)} y1={base + 2} y2={base + 8} />
        ))}
        {ticks.map((t, i) => (
          <text
            key={t}
            className="tick"
            x={x(t)}
            y={height - 6}
            textAnchor={i === 0 ? 'start' : i === ticks.length - 1 && x(t) > width - 40 ? 'end' : 'middle'}
          >
            {formatMetric(metric, t)}
          </text>
        ))}
      </svg>
    </div>
  )
}
