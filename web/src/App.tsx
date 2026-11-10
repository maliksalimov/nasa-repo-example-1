import { useCallback, useEffect, useState } from 'react'
import { loadData, refreshData } from './api'
import { displayName, fmt } from './format'
import type { Payload } from './types'
import { BaselineSection } from './components/BaselineSection'
import { DistanceStrip } from './components/DistanceStrip'
import { RiskSection } from './components/RiskSection'
import { UpcomingSection } from './components/UpcomingSection'
import { WeekSection } from './components/WeekSection'

type RefreshState = { kind: 'idle' } | { kind: 'busy' } | { kind: 'done'; text: string; ok: boolean }

export default function App() {
  const [data, setData] = useState<Payload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refresh, setRefresh] = useState<RefreshState>({ kind: 'idle' })

  const load = useCallback(async () => {
    try {
      setData(await loadData())
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function onRefresh() {
    setRefresh({ kind: 'busy' })
    try {
      const result = await refreshData()
      const failed = [
        !result.recent && 'NASA NeoWs',
        !result.sentry && 'Sentry',
        !result.close_approach && 'Close Approach',
      ].filter(Boolean)
      await load()
      setRefresh(
        failed.length === 0
          ? { kind: 'done', ok: true, text: 'Data yeniləndi.' }
          : { kind: 'done', ok: false, text: `${failed.join(', ')} cavab vermədi, köhnə data göstərilir.` },
      )
    } catch (reason) {
      setRefresh({ kind: 'done', ok: false, text: reason instanceof Error ? reason.message : String(reason) })
    }
  }

  return (
    <>
      <header className="masthead">
        <span className="wordmark">Space App</span>
        <div className="masthead-actions">
          {data?.recent && (
            <span className="updated">Yenilənib {fmt.dateTime(data.recent.updated_at)}</span>
          )}
          <button type="button" className="button" onClick={onRefresh} disabled={refresh.kind === 'busy' || !!error}>
            {refresh.kind === 'busy' ? 'Yenilənir…' : 'Datanı yenilə'}
          </button>
        </div>
      </header>
      {refresh.kind === 'done' && (
        <p className={refresh.ok ? 'notice' : 'notice notice-signal'} role="status">
          {refresh.text}
        </p>
      )}

      <main>
        {error ? (
          <ErrorState message={error} onRetry={load} />
        ) : !data ? (
          <LoadingState />
        ) : !data.recent ? (
          <p className="empty">
            Asteroid datası hələ yoxdur. "Datanı yenilə" düyməsi son 7 günü NASA-dan götürəcək.
          </p>
        ) : (
          <Dashboard data={data as Payload & { recent: NonNullable<Payload['recent']> }} />
        )}
      </main>

      <footer className="footer">
        <p>
          Data: NASA NeoWs (api.nasa.gov), NASA JPL CNEOS Sentry və Close Approach (ssd-api.jpl.nasa.gov). Hesablamalar
          bu tətbiqdədir, NASA-nın rəsmi qiymətləndirməsi deyil.
        </p>
      </footer>
    </>
  )
}

function Dashboard({ data }: { data: Payload & { recent: NonNullable<Payload['recent']> } }) {
  const asteroids = data.recent.asteroids
  const closest = asteroids.reduce((a, b) => (b.distance_ld < a.distance_ld ? b : a))
  const calm = data.sentry ? data.sentry.torino_positive.length === 0 : null

  return (
    <>
      {data.is_sample && (
        <p className="notice notice-signal" role="alert">
          Bu nümunə datadır, real NASA datası deyil. .env faylına NASA_API_KEY yaz və "Datanı yenilə" düyməsini bas.
        </p>
      )}
      <section className="hero" aria-labelledby="hero-title">
        <h1 id="hero-title">Bu həftə {asteroids.length} asteroid Yerin yanından keçdi.</h1>
        <p className="hero-sub">
          Ən yaxını, {displayName(closest.name)}, Aydan {fmt.one(closest.distance_ld)} dəfə uzaqda idi.{' '}
          {calm === true && 'Yerə dəymə riski olan obyekt yoxdur.'}
          {calm === false && 'Sentry siyahısında diqqət tələb edən obyekt var, aşağıya bax.'}
        </p>
        <DistanceStrip asteroids={asteroids} />
      </section>
      <WeekSection asteroids={asteroids} start={data.recent.start} end={data.recent.end} />
      <BaselineSection baseline={data.baseline} asteroids={asteroids} />
      <RiskSection sentry={data.sentry} />
      <UpcomingSection data={data.close_approach} />
    </>
  )
}

function LoadingState() {
  return (
    <div className="loading" aria-busy="true" aria-label="Data yüklənir">
      <div className="skeleton skeleton-title" />
      <div className="skeleton skeleton-line" />
      <div className="skeleton skeleton-strip" />
    </div>
  )
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="error-state" role="alert">
      <h1>Serverdən data gəlmədi.</h1>
      <p>
        Terminalda layihə qovluğunda <code>.venv/bin/python serve.py</code> işlədiyini yoxla, sonra yenidən cəhd et.
      </p>
      <p className="footnote">Xəta: {message}</p>
      <button type="button" className="button" onClick={onRetry}>
        Yenidən cəhd et
      </button>
    </div>
  )
}
