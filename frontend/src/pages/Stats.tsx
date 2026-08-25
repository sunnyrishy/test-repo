import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchStats } from '../services/api'
import type { Stats as StatsType } from '../types/job'

export default function Stats() {
  const [stats, setStats] = useState<StatsType | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch((err: Error) => setError(err.message))
  }, [])

  if (error) return <p className="text-sm text-red-800">{error}</p>
  if (!stats) return <p className="text-sm text-slate-500">Loading…</p>

  const funnel: [string, number][] = [
    ['Discovered this week', stats.discovered_this_week],
    ['Duplicates merged', stats.duplicates_merged],
    ['Failed hard filters', stats.rejected],
    ['Sent to AI verification', stats.verified],
    ['Passed verification', stats.verified_pass],
    ['Excellent matches', stats.excellent_matches],
  ]

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <h1 className="text-lg font-semibold">Statistics</h1>
        <Link to="/" className="text-sm text-slate-600 underline-offset-2 hover:underline">
          ← Dashboard
        </Link>
      </div>

      <section className="mt-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Funnel</h2>
        <ul className="mt-2 max-w-md text-sm">
          {funnel.map(([label, value]) => (
            <li key={label} className="flex justify-between border-b border-slate-100 py-1.5">
              <span className="text-slate-600">{label}</span>
              <span className="font-medium tabular-nums">{value}</span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-sm text-slate-600">
          Average score:{' '}
          <span className="tabular-nums">
            {stats.average_score === null ? '—' : stats.average_score.toFixed(1)}
          </span>{' '}
          · dashboard threshold {stats.min_match_score}
        </p>
      </section>

      <div className="mt-6 grid gap-6 sm:grid-cols-3">
        <Breakdown title="By source" data={stats.by_source} />
        <Breakdown title="By rejection reason" data={stats.by_rejection_reason} />
        <Breakdown title="By match quality" data={stats.by_classification} />
      </div>

      <section className="mt-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          AI verification
        </h2>
        <ul className="mt-2 max-w-md text-sm">
          {[
            ['Passed', stats.verified_pass],
            ['Failed', stats.verified_fail],
            ['Needs review', stats.verified_review],
            ['Errors', stats.verification_errors],
          ].map(([label, value]) => (
            <li key={label as string} className="flex justify-between border-b border-slate-100 py-1.5">
              <span className="text-slate-600">{label as string}</span>
              <span className="tabular-nums">{value as number}</span>
            </li>
          ))}
        </ul>
      </section>

      {stats.last_run && (
        <section className="mt-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Last discovery run
          </h2>
          <p className="mt-2 text-sm text-slate-700">
            Started {new Date(stats.last_run.started_at).toLocaleString()} ·{' '}
            {stats.last_run.discovered} discovered, {stats.last_run.duplicates} duplicates,{' '}
            {stats.last_run.hard_filter_failures} hard-filtered, {stats.last_run.passed_filters}{' '}
            passed
          </p>
          {stats.last_run.per_source && (
            <pre className="mt-2 overflow-x-auto border border-slate-200 bg-slate-50 p-3 text-xs">
              {stats.last_run.per_source}
            </pre>
          )}
          {stats.last_run.errors && (
            <pre className="mt-2 overflow-x-auto border border-red-200 bg-red-50 p-3 text-xs text-red-900">
              {stats.last_run.errors}
            </pre>
          )}
        </section>
      )}
    </div>
  )
}

function Breakdown({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1])
  return (
    <section>
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
      {entries.length === 0 ? (
        <p className="mt-2 text-sm text-slate-400">No data yet</p>
      ) : (
        <ul className="mt-2 text-sm">
          {entries.map(([label, value]) => (
            <li key={label} className="flex justify-between border-b border-slate-100 py-1">
              <span className="text-slate-600">{label}</span>
              <span className="tabular-nums">{value}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
