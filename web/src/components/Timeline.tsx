import { useMemo } from 'react'
import { max, min } from 'd3-array'
import { scaleLog, scaleSqrt, scaleUtc } from 'd3-scale'
import { fmt } from '../format'
import type { CloseApproach } from '../types'
import { tipHandlers, useTooltip } from '../Tooltip'
import { useWidth } from '../useWidth'

const M = { top: 16, right: 16, bottom: 34, left: 44 }
const Y_TICKS = [0.5, 1, 2, 5, 10, 20]

/** Upcoming passes over time. Anything below the Moon line is closer than the Moon. */
export function Timeline({ items }: { items: CloseApproach[] }) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(800)
  const { containerRef, show, hide, element } = useTooltip()
  const height = 300

  const { x, y, r } = useMemo(() => {
    const times = items.map((i) => Date.parse(`${i.datetime_utc}Z`))
    const x = scaleUtc()
      .domain([new Date(Math.min(...times) - 864e5), new Date(Math.max(...times) + 864e5)])
      .range([M.left, width - M.right])
    const y = scaleLog()
      .domain([Math.min(0.5, (min(items, (i) => i.distance_ld) ?? 1) * 0.8), (max(items, (i) => i.distance_ld) ?? 20) * 1.15])
      .range([height - M.bottom, M.top])
    const r = scaleSqrt().domain([0, max(items, (i) => i.diameter_m ?? 0) ?? 1]).range([2.5, 12])
    return { x, y, r }
  }, [items, width])

  const yTicks = Y_TICKS.filter((t) => t >= y.domain()[0] && t <= y.domain()[1])

  return (
    <div ref={wrapRef}>
      <div ref={containerRef} className="chart-frame">
        <svg width={width} height={height} role="img" aria-label={`Növbəti ${items.length} yaxın keçid zaman üzrə`}>
          {yTicks.map((t) => (
            <g key={t} className={t === 1 ? 'moon-line' : 'grid-line'} transform={`translate(0,${y(t)})`}>
              <line x1={M.left} x2={width - M.right} />
              <text x={M.left - 8} dy="0.32em" textAnchor="end">{fmt.one(t)}</text>
            </g>
          ))}
          <text className="axis-title moon-label" x={width - M.right} y={y(1) - 6} textAnchor="end">
            Ay məsafəsi
          </text>
          {x.ticks(width < 640 ? 3 : 6).map((t) => (
            <text key={t.toISOString()} className="tick" x={x(t)} y={height - 10} textAnchor="middle">
              {fmt.day(t.toISOString())}
            </text>
          ))}
          {items.map((item) => (
            <circle
              key={`${item.designation}-${item.datetime_utc}`}
              cx={x(Date.parse(`${item.datetime_utc}Z`))}
              cy={y(item.distance_ld)}
              r={r(item.diameter_m ?? 0)}
              className={item.distance_ld < 1 ? 'dot dot-signal' : 'dot'}
              aria-label={`${item.designation}, ${fmt.ld(item.distance_ld)} Ay məsafəsi`}
              {...tipHandlers(
                show,
                hide,
                <>
                  <strong>{item.designation}</strong>
                  <span>{fmt.dateTime(`${item.datetime_utc}Z`)}</span>
                  <span>
                    {fmt.ld(item.distance_ld)} Ay məsafəsi, {fmt.km(item.distance_km)}
                  </span>
                  <span>
                    Diametr {item.diameter_estimated ? 'təxminən ' : ''}
                    {fmt.meters(item.diameter_m)}, sürət {fmt.one(item.velocity_km_s)} km/s
                  </span>
                </>,
              )}
            />
          ))}
        </svg>
        {element}
      </div>
    </div>
  )
}
