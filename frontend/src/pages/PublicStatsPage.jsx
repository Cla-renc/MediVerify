import { useCallback, useEffect, useState } from 'react'
import { Activity, AlertTriangle, Package, RefreshCw, ShieldCheck, Store } from 'lucide-react'
import { getPublicStatistics } from '../services/api'

const STAT_CARDS = [
  { key: 'scans_today', label: 'Scans today', icon: Activity, color: 'text-brand-300' },
  { key: 'genuine_percent_today', label: 'Genuine today', suffix: '%', icon: ShieldCheck, color: 'text-emerald-300' },
  { key: 'clone_alerts_pending', label: 'Pending clone alerts', icon: AlertTriangle, color: 'text-violet-300' },
  { key: 'registered_products', label: 'Registered products', icon: Package, color: 'text-amber-300' },
  { key: 'registered_batches', label: 'Registered batches', icon: Package, color: 'text-cyan-300' },
  { key: 'registered_pharmacies', label: 'Registered pharmacies', icon: Store, color: 'text-pink-300' },
]

export default function PublicStatsPage() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  const refresh = useCallback(async () => {
    setRefreshing(true)
    try {
      const response = await getPublicStatistics()
      setStats(response.data)
      setError('')
    } catch {
      setError('Could not load MediVerify statistics. Please try again.')
    } finally {
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const timer = window.setInterval(refresh, 30000)
    return () => window.clearInterval(timer)
  }, [refresh])

  return (
    <main className="min-h-[calc(100dvh-64px)] bg-gradient-dark px-4 py-10">
      <section className="mx-auto max-w-5xl">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-brand-300">Public dashboard</p>
            <h1 className="mt-2 text-3xl font-black text-white">MediVerify at a glance</h1>
            <p className="mt-2 text-sm text-gray-400">
              Aggregate verification activity. This dashboard refreshes every 30 seconds.
            </p>
          </div>
          <button type="button" onClick={refresh} disabled={refreshing} className="btn-secondary text-xs">
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {error && <p role="alert" className="mb-5 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {STAT_CARDS.map(({ key, label, suffix = '', icon: Icon, color }) => (
            <article key={key} className="glass rounded-2xl border border-white/5 p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-400">{label}</p>
                <Icon size={18} className={color} aria-hidden="true" />
              </div>
              <p className="mt-4 text-3xl font-black text-white">
                {stats ? `${Number(stats[key] || 0).toLocaleString()}${suffix}` : '—'}
              </p>
            </article>
          ))}
        </div>

        <p className="mt-6 text-xs text-gray-600">
          {stats?.as_of ? `Updated ${new Date(stats.as_of).toLocaleString()}.` : 'Statistics are not medical or regulatory certification.'}
          {' '}Counts reflect records currently available in the MediVerify database.
        </p>
      </section>
    </main>
  )
}
