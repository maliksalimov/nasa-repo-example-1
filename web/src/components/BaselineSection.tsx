import { METRIC_LABELS, displayName, fmt, formatMetric } from '../format'
import type { Asteroid, Baseline, MetricKey } from '../types'
import { Histogram } from './Histogram'

const METRICS: MetricKey[] = ['diameter_m', 'velocity_km_s', 'miss_distance_km']

function changeText(ratio: number) {
  const percent = Math.round((ratio - 1) * 100)
  if (Math.abs(percent) < 3) return 'normaya yaxındır'
  return percent > 0 ? `normadan ${percent}% çoxdur` : `normadan ${Math.abs(percent)}% azdır`
}

export function BaselineSection({ baseline, asteroids }: { baseline: Baseline; asteroids: Asteroid[] }) {
  const outliers = asteroids.filter((a) => a.is_outlier)
  const fromHistory = baseline.source === 'history'
  // Inclusive day count: 12 Oct to 8 Nov is 28 days, so 4 weeks.
  const weeks = Math.round(((Date.parse(baseline.end) - Date.parse(baseline.start)) / 864e5 + 1) / 7)

  return (
    <section className="section" aria-labelledby="baseline-title">
      <h2 id="baseline-title">Bu həftə adi həftədirmi?</h2>
      <p className="lead">
        {fromHistory
          ? `Norma son ${weeks} həftənin ${fmt.int(baseline.count)} asteroidindən hesablanıb (${fmt.dayLong(baseline.start)} ilə ${fmt.dayLong(baseline.end)} arası).`
          : 'Tarixçə yoxdur, ona görə norma yalnız bu həftədən hesablanır. Daha dəqiq norma üçün tarixçə yığ: data_loader.py --history 4.'}
      </p>

      <div className="metrics">
        {METRICS.map((metric) => {
          const stats = baseline.metrics[metric]
          const comparison = baseline.comparison?.find((c) => c.metric === metric)
          return (
            <figure key={metric} className="metric">
              <figcaption>
                <span className="metric-name">{METRIC_LABELS[metric]}</span>
                <span className="metric-value">{formatMetric(metric, stats.median)}</span>
                <span className="metric-range">
                  Normal aralıq {formatMetric(metric, stats.q1)} ilə {formatMetric(metric, stats.q3)} arası
                </span>
              </figcaption>
              <Histogram metric={metric} stats={stats} recent={asteroids.map((a) => a[metric])} />
              {comparison && (
                <p className="metric-compare">
                  Bu həftənin medianı {formatMetric(metric, comparison.recent_median)}, {changeText(comparison.ratio)}.
                </p>
              )}
            </figure>
          )
        })}
      </div>
      <p className="footnote">
        Rəngli zolaq normal aralıqdır (ortadakı 50%). Xətt mediandır. Oxun altındakı qısa cizgilər bu həftənin asteroidləridir.
      </p>

      <div className="outliers">
        <h3>Normadan kənar keçənlər</h3>
        {outliers.length === 0 ? (
          <p>Bu həftə heç bir asteroid normal aralıqdan uzaq deyil.</p>
        ) : (
          <ul>
            {outliers.map((a) => (
              <li key={a.name}>
                <strong>{displayName(a.name)}</strong>,{' '}
                {a.outlier_reasons
                  .map((reason) => {
                    const stats = baseline.metrics[reason]
                    const above = a[reason] > stats.upper_fence
                    const limit = formatMetric(reason, above ? stats.upper_fence : stats.lower_fence)
                    return `${METRIC_LABELS[reason].toLowerCase()} ${formatMetric(reason, a[reason])} (${above ? 'yuxarı' : 'aşağı'} hədd ${limit})`
                  })
                  .join(', ')}
                .
              </li>
            ))}
          </ul>
        )}
      </div>

      {baseline.weekly && baseline.weekly.length > 1 && (
        <div className="weekly">
          <h3>Həftə-həftə</h3>
          <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Həftə</th>
                <th scope="col" className="num">Asteroid</th>
                <th scope="col" className="num">Potensial təhlükəli</th>
                <th scope="col" className="num">Median diametr</th>
              </tr>
            </thead>
            <tbody>
              {baseline.weekly.map((w) => (
                <tr key={w.week}>
                  <th scope="row">{fmt.dayLong(w.week)} həftəsi</th>
                  <td className="num">{w.count}</td>
                  <td className="num">{fmt.int(w.hazardous_pct)}%</td>
                  <td className="num">{fmt.int(w.median_diameter_m)} m</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}
    </section>
  )
}
