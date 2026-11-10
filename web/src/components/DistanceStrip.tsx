import { useMemo } from 'react'
import { scaleLog, scaleSqrt } from 'd3-scale'
import { max } from 'd3-array'
import { displayName, fmt } from '../format'
import type { Asteroid } from '../types'
import { tipHandlers, useTooltip } from '../Tooltip'
import { useWidth } from '../useWidth'
import { AsteroidTip } from './AsteroidTip'

const EARTH_X = 26
const TICKS = [1, 2, 5, 10, 20, 50, 100, 200, 500]

/** Stable pseudo-random number in [0, 1) from a string, so dots keep their lane. */
function lane(name: string) {
  let hash = 2166136261
  for (const char of name) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619)
  return ((hash >>> 0) % 1000) / 1000
}

/**
 * The page's signature element: Earth on the left, the Moon's distance as a
 * reference line, and every asteroid of the week placed by how far it passed.
 */
export function DistanceStrip({ asteroids }: { asteroids: Asteroid[] }) {
  const [wrapRef, width] = useWidth<HTMLDivElement>()
  const { containerRef, show, hide, element } = useTooltip()

  const height = width < 640 ? 230 : 250
  const top = 28
  const bottom = height - 40
  const farthest = max(asteroids, (a) => a.distance_ld) ?? 100

  const x = useMemo(
    () => scaleLog().domain([0.6, farthest * 1.25]).range([EARTH_X + 40, width - 12]),
    [farthest, width],
  )
  const radius = useMemo(
    () => scaleSqrt().domain([0, max(asteroids, (a) => a.diameter_m) ?? 1]).range([2.5, width < 640 ? 9 : 13]),
    [asteroids, width],
  )
  const ticks = TICKS.filter((tick) => tick >= x.domain()[0] && tick <= x.domain()[1])
  const ordered = useMemo(() => [...asteroids].sort((a, b) => a.distance_ld - b.distance_ld), [asteroids])

  return (
    <div ref={wrapRef} className="strip">
      <div ref={containerRef} className="chart-frame">
        <svg
          width={width}
          height={height}
          role="img"
          aria-label={`${asteroids.length} asteroidin Yerdən məsafəsi, Ay məsafəsi ilə müqayisədə`}
        >
          {ticks.map((tick) => (
            <g key={tick} transform={`translate(${x(tick)},0)`} className={tick === 1 ? 'moon-line' : 'grid-line'}>
              <line y1={top - 10} y2={bottom} />
              {(tick === 1 || tick === 10 || tick === 100) && (
                <text y={bottom + 20} textAnchor="middle">
                  {tick === 1 ? 'Ay' : `${tick} Ay məsafəsi`}
                </text>
              )}
            </g>
          ))}

          <g className="earth" transform={`translate(${EARTH_X},${(top + bottom) / 2})`}>
            <circle r={13} />
            <text y={bottom - (top + bottom) / 2 + 20} textAnchor="middle">
              Yer
            </text>
          </g>

          {ordered.map((asteroid, index) => {
            const cx = x(asteroid.distance_ld)
            const cy = top + 8 + lane(asteroid.name) * (bottom - top - 16)
            const middle = (top + bottom) / 2
            return (
              <g
                key={asteroid.name}
                className="flyby"
                style={
                  {
                    transform: `translate(${cx}px, ${cy}px)`,
                    '--from': `translate(${EARTH_X}px, ${middle}px)`,
                    animationDelay: `${index * 14}ms`,
                  } as React.CSSProperties
                }
              >
                <circle
                  r={radius(asteroid.diameter_m)}
                  className={asteroid.is_hazardous ? 'dot dot-signal' : 'dot'}
                  aria-label={`${displayName(asteroid.name)}, ${fmt.ld(asteroid.distance_ld)} Ay məsafəsi`}
                  {...tipHandlers(show, hide, <AsteroidTip asteroid={asteroid} />)}
                />
                {index === 0 && (
                  <text className="closest-label" x={-radius(asteroid.diameter_m) - 8} dy="0.32em" textAnchor="end">
                    Ən yaxın: {fmt.one(asteroid.distance_ld)}
                  </text>
                )}
              </g>
            )
          })}
        </svg>
        {element}
      </div>
      <p className="legend">
        <span className="key key-signal" aria-hidden="true" /> Potensial təhlükəli (NASA təsnifatı)
        <span className="key" aria-hidden="true" /> Digərləri
        <span className="legend-note">Dairənin ölçüsü diametri göstərir. Şkala loqarifmikdir.</span>
      </p>
    </div>
  )
}
