import { useMemo, useState } from 'react'
import { displayName, fmt } from '../format'
import type { Asteroid } from '../types'
import { Scatter } from './Scatter'

const COLLAPSED_ROWS = 8

export function WeekSection({ asteroids, start, end }: { asteroids: Asteroid[]; start: string; end: string }) {
  const days = useMemo(() => [...new Set(asteroids.map((a) => a.date))].sort(), [asteroids])
  const [day, setDay] = useState<string | null>(null)
  const [onlyHazardous, setOnlyHazardous] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const filtered = asteroids.filter(
    (a) => (day === null || a.date === day) && (!onlyHazardous || a.is_hazardous),
  )
  const rows = expanded ? filtered : filtered.slice(0, COLLAPSED_ROWS)

  return (
    <section className="section" aria-labelledby="week-title">
      <h2 id="week-title">Hansılarına diqqət etmək lazımdır?</h2>
      <p className="lead">
        {fmt.dayLong(start)} ilə {fmt.dayLong(end)} arası. Böyük və yaxın keçənlər qrafikin sol yuxarı küncündədir.
      </p>

      <div className="filters" role="group" aria-label="Filtr">
        <div className="chips" role="radiogroup" aria-label="Gün">
          <button type="button" role="radio" aria-checked={day === null} onClick={() => setDay(null)}>
            Bütün həftə
          </button>
          {days.map((d) => (
            <button key={d} type="button" role="radio" aria-checked={day === d} onClick={() => setDay(d)}>
              {fmt.day(d)}
            </button>
          ))}
        </div>
        <label className="toggle">
          <input type="checkbox" checked={onlyHazardous} onChange={(e) => setOnlyHazardous(e.target.checked)} />
          Yalnız potensial təhlükəlilər
        </label>
      </div>

      {filtered.length === 0 ? (
        <p className="empty">Bu filtrə uyğun asteroid yoxdur. Başqa gün seç və ya filtri söndür.</p>
      ) : (
        <div className="week-grid">
          <Scatter asteroids={filtered} domain={asteroids} />
          <div className="ranking">
            <table>
              <caption>Diqqət sırası, {filtered.length} asteroid</caption>
              <thead>
                <tr>
                  <th scope="col">Ad</th>
                  <th scope="col" className="num">Diametr</th>
                  <th scope="col" className="num">Ay məs.</th>
                  <th scope="col" className="num">Bal</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((a) => (
                  <tr key={a.name}>
                    <th scope="row">
                      <span className="name">{displayName(a.name)}</span>
                      <span className="sub">
                        {fmt.day(a.date)}
                        {a.is_hazardous && <span className="signal-text">, potensial təhlükəli</span>}
                        {a.is_outlier && <span>, normadan kənar</span>}
                      </span>
                    </th>
                    <td className="num">{fmt.int(a.diameter_m)} m</td>
                    <td className="num">{fmt.one(a.distance_ld)}</td>
                    <td className="num">{fmt.int(a.attention_score)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length > COLLAPSED_ROWS && (
              <button type="button" className="text-button" onClick={() => setExpanded(!expanded)}>
                {expanded ? 'Qısalt' : `Hamısını göstər (${filtered.length})`}
              </button>
            )}
            <p className="footnote">
              Bal 0-100 arasıdır və yalnız sıralama üçündür, toqquşma ehtimalı deyil. Ölçü və yaxınlıq 35-ər, NASA
              təhlükə işarəsi və Sentry siyahısı 15-ər bal verir.
            </p>
          </div>
        </div>
      )}
    </section>
  )
}
