import { useMemo } from 'react'
import { extent } from 'd3-array'
import { scaleLog } from 'd3-scale'
import { fmt } from '../format'
import type { Asteroid } from '../types'
import { tipHandlers, useTooltip } from '../Tooltip'
import { useWidth } from '../useWidth'
import { AsteroidTip } from './AsteroidTip'

const M = { top: 16, right: 16, bottom: 44, left: 56 }
const X_TICKS = [5, 10, 20, 50, 100, 200]
const Y_TICKS = [3, 10, 30, 100, 300, 1000]

/** Distance against size: the top-left corner holds the big and close ones. */
export function Scatter({ asteroids, domain }: { asteroids: Asteroid[]; domain: Asteroid[] }) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(600)
  const { containerRef, show, hide, element } = useTooltip()
  const height = 360

  // Axes come from the whole week so filtering does not rescale the chart.
  const { x, y } = useMemo(() => {
    const [minLd, maxLd] = extent(domain, (a) => a.distance_ld) as [number, number]
    const [minD, maxD] = extent(domain, (a) => a.diameter_m) as [number, number]
    return {
      x: scaleLog().domain([minLd * 0.8, maxLd * 1.2]).range([M.left, width - M.right]),
      y: scaleLog().domain([minD * 0.7, maxD * 1.4]).range([height - M.bottom, M.top]),
    }
  }, [domain, width])

  const xTicks = X_TICKS.filter((t) => t >= x.domain()[0] && t <= x.domain()[1])
  const yTicks = Y_TICKS.filter((t) => t >= y.domain()[0] && t <= y.domain()[1])

  return (
    <div ref={wrapRef} className="scatter">
      <div ref={containerRef} className="chart-frame">
        <svg width={width} height={height} role="img" aria-label="Asteroidlərin məsafəsi və diametri">
          {xTicks.map((t) => (
            <g key={`x${t}`} className="grid-line" transform={`translate(${x(t)},0)`}>
              <line y1={M.top} y2={height - M.bottom} />
              <text y={height - M.bottom + 18} textAnchor="middle">{t}</text>
            </g>
          ))}
          {yTicks.map((t) => (
            <g key={`y${t}`} className="grid-line" transform={`translate(0,${y(t)})`}>
              <line x1={M.left} x2={width - M.right} />
              <text x={M.left - 8} dy="0.32em" textAnchor="end">{fmt.int(t)}</text>
            </g>
          ))}
          <text className="axis-title" x={width - M.right} y={height - 6} textAnchor="end">
            Yerdən məsafə, Ay məsafəsi ilə
          </text>
          <text className="axis-title" x={M.left + 6} y={M.top + 4} dy="0.32em">
            Diametr, m
          </text>

          {asteroids.map((asteroid) => (
            <g key={asteroid.name} transform={`translate(${x(asteroid.distance_ld)},${y(asteroid.diameter_m)})`}>
              {asteroid.is_outlier && <circle r={11} className="outlier-ring" />}
              <circle
                r={5.5}
                className={asteroid.is_hazardous ? 'dot dot-signal' : 'dot'}
                aria-label={asteroid.name}
                {...tipHandlers(show, hide, <AsteroidTip asteroid={asteroid} />)}
              />
            </g>
          ))}
        </svg>
        {element}
      </div>
    </div>
  )
}
