import { displayName, fmt } from '../format'
import type { Asteroid } from '../types'

export function AsteroidTip({ asteroid }: { asteroid: Asteroid }) {
  return (
    <>
      <strong>{displayName(asteroid.name)}</strong>
      <span>{fmt.dayLong(asteroid.date)}</span>
      <span>
        {fmt.ld(asteroid.distance_ld)} Ay məsafəsi, {fmt.km(asteroid.miss_distance_km)}
      </span>
      <span>
        Diametr təxminən {fmt.meters(asteroid.diameter_m)}, sürət {fmt.one(asteroid.velocity_km_s)} km/s
      </span>
      {asteroid.is_hazardous && <span className="tip-signal">NASA bunu potensial təhlükəli sayır</span>}
    </>
  )
}
