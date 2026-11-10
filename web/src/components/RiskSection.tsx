import { displayName, fmt } from '../format'
import type { Sentry } from '../types'

export function RiskSection({ sentry }: { sentry: Sentry | null }) {
  if (!sentry) {
    return (
      <section className="section" aria-labelledby="risk-title">
        <h2 id="risk-title">Yerə dəyə biləcək obyektlər</h2>
        <p className="empty">Sentry datası yoxdur. Yuxarıdakı "Datanı yenilə" düyməsi onu JPL-dən götürəcək.</p>
      </section>
    )
  }

  const calm = sentry.torino_positive.length === 0
  return (
    <section className="section" aria-labelledby="risk-title">
      <h2 id="risk-title">Yerə dəyə biləcək obyektlər</h2>
      <p className={calm ? 'verdict' : 'verdict verdict-signal'}>
        {calm
          ? 'Hazırda Torino şkalasında 0-dan yuxarı heç bir obyekt yoxdur.'
          : `Torino şkalasında 0-dan yuxarı ${sentry.torino_positive.length} obyekt var: ${sentry.torino_positive.join(', ')}.`}
      </p>
      <p className="lead">
        NASA JPL-in Sentry sistemi gələcək 100 ildə Yerə dəymə ehtimalı sıfır olmayan {fmt.int(sentry.count)} obyekti
        izləyir. Torino 0 o deməkdir ki, ehtimal o qədər kiçikdir ki, narahatlığa səbəb yoxdur.
      </p>

      <div className="risk-grid">
        <div className="table-wrap">
        <table>
          <caption>Palermo şkalasına görə ilk {sentry.top.length}</caption>
          <thead>
            <tr>
              <th scope="col">Ad</th>
              <th scope="col">Mümkün illər</th>
              <th scope="col" className="num">Ehtimal</th>
              <th scope="col" className="num">Palermo</th>
              <th scope="col" className="num">Diametr</th>
            </tr>
          </thead>
          <tbody>
            {sentry.top.map((item) => (
              <tr key={item.name}>
                <th scope="row">{item.name}</th>
                <td>{item.years.replace(/^(\d+)-\1$/, '$1')}</td>
                <td className="num">{fmt.probability(item.impact_probability)}</td>
                <td className="num">{fmt.two(item.palermo_cum)}</td>
                <td className="num">{fmt.meters(item.diameter_m)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>

        <aside className="risk-notes">
          <h3>Bu həftə keçənlərdən</h3>
          {sentry.recent_matches.length > 0 ? (
            <ul>
              {sentry.recent_matches.map((m) => (
                <li key={m.name}>
                  <strong>{displayName(m.name)}</strong> {fmt.dayLong(m.date)} günü {fmt.one(m.distance_ld)} Ay məsafəsindən
                  keçdi. Sentry-də dəymə ehtimalı {fmt.probability(m.sentry_impact_probability)},{' '}
                  {m.sentry_years.replace(/^(\d+)-\1$/, '$1')} illəri üçün.
                </li>
              ))}
            </ul>
          ) : sentry.recent_flagged.length > 0 ? (
            <p>
              NeoWs bunları Sentry obyekti kimi işarələyib: {sentry.recent_flagged.map(displayName).join(', ')}. Sentry
              siyahısında ad uyğunluğu tapılmadı.
            </p>
          ) : (
            <p>Bu həftə keçən asteroidlərin heç biri Sentry siyahısında deyil.</p>
          )}
          <h3>Şkalaları necə oxumaq</h3>
          <p>
            Palermo -2-dən aşağıdırsa, risk fon səviyyəsindən çox kiçikdir. 0-dan yuxarı olsa, xüsusi diqqət tələb edir.
            Torino 0-10 arası ictimaiyyət üçün şkaladır.
          </p>
        </aside>
      </div>
    </section>
  )
}
