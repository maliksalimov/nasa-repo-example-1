import { fmt } from '../format'
import type { CloseApproach } from '../types'
import { Timeline } from './Timeline'

const NEAREST = 5

export function UpcomingSection({ data }: { data: { items: CloseApproach[] } | null }) {
  const items = data?.items ?? []
  const insideMoon = items.filter((i) => i.distance_ld < 1)
  const nearest = [...items].sort((a, b) => a.distance_ld - b.distance_ld).slice(0, NEAREST)

  return (
    <section className="section" aria-labelledby="upcoming-title">
      <h2 id="upcoming-title">Növbəti 60 gündə kim yaxınlaşacaq?</h2>
      {!data ? (
        <p className="empty">Yaxınlaşma datası yoxdur. Yuxarıdakı "Datanı yenilə" düyməsi onu JPL-dən götürəcək.</p>
      ) : items.length === 0 ? (
        <p className="empty">Növbəti 60 gündə 19,5 Ay məsafəsindən yaxın keçid gözlənilmir.</p>
      ) : (
        <>
          <p className="lead">
            19,5 Ay məsafəsi (0,05 AB) daxilində {items.length} keçid gözlənilir.{' '}
            {insideMoon.length > 0
              ? `${insideMoon.length} asteroid Aydan da yaxın keçəcək, onlar qrafikdə rənglidir.`
              : 'Heç biri Aydan yaxın keçməyəcək.'}
          </p>
          <Timeline items={items} />
          <div className="table-wrap nearest">
          <table>
            <caption>Ən yaxın {nearest.length} keçid</caption>
            <thead>
              <tr>
                <th scope="col">Ad</th>
                <th scope="col">Vaxt</th>
                <th scope="col" className="num">Ay məs.</th>
                <th scope="col" className="num">Diametr</th>
                <th scope="col" className="num">Sürət</th>
              </tr>
            </thead>
            <tbody>
              {nearest.map((item) => (
                <tr key={`${item.designation}-${item.datetime_utc}`}>
                  <th scope="row" className={item.distance_ld < 1 ? 'signal-text' : undefined}>{item.designation}</th>
                  <td>{fmt.dateTime(`${item.datetime_utc}Z`)}</td>
                  <td className="num">{fmt.ld(item.distance_ld)}</td>
                  <td className="num">
                    {item.diameter_estimated && item.diameter_m != null ? '≈ ' : ''}
                    {fmt.meters(item.diameter_m)}
                  </td>
                  <td className="num">{fmt.one(item.velocity_km_s)} km/s</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          <p className="footnote">
            ≈ işarəli diametrlər parlaqlıqdan təxmin olunub (albedo 0,14), real ölçü 2 dəfəyə qədər fərqli ola bilər.
          </p>
        </>
      )}
    </section>
  )
}
