import { useCallback, useEffect, useState } from 'react'
import JobRow from '../components/JobRow'
import { fetchJobs, fetchStats, runDiscovery, setJobStatus } from '../services/api'
import type { Job, Stats } from '../types/job'

const PAGE_SIZE = 25

const TABS = [
  { key: '', label: 'All' },
  { key: 'NEW', label: 'New' },
  { key: 'SAVED', label: 'Saved' },
  { key: 'APPLIED', label: 'Applied' },
  { key: 'INTERVIEW', label: 'Interview' },
  { key: 'REJECTED', label: 'Rejected' },
]

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [stats, setStats] = useState<Stats | null>(null)
  const [search, setSearch] = useState('')
  const [tab, setTab] = useState('')
  const [postedWithin, setPostedWithin] = useState('')
  const [workplace, setWorkplace] = useState('')
  const [sort, setSort] = useState('newest')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const page = await fetchJobs({
        search: search || undefined,
        status: tab || undefined,
        workplace_type: workplace || undefined,
        posted_within_hours: postedWithin ? Number(postedWithin) : undefined,
        sort,
        limit: PAGE_SIZE,
        offset,
      })
      setJobs(page.items)
      setTotal(page.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load jobs')
    }
  }, [search, tab, workplace, postedWithin, sort, offset])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    fetchStats().then(setStats).catch(() => setStats(null))
  }, [jobs])

  const onStatusChange = async (id: number, status: string) => {
    await setJobStatus(id, status)
    void load()
  }

  const onRefresh = async () => {
    setBusy(true)
    setError(null)
    try {
      await runDiscovery()
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Discovery run failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <h1 className="text-lg font-semibold">Dashboard</h1>
        <button
          type="button"
          onClick={onRefresh}
          disabled={busy}
          className="border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
        >
          {busy ? 'Running…' : 'Run discovery'}
        </button>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-px border border-slate-200 bg-slate-200 sm:grid-cols-4">
        <Metric label="Discovered today" value={stats?.discovered_today} />
        <Metric label="This week" value={stats?.discovered_this_week} />
        <Metric label="Passed filters" value={stats?.passed_filters} />
        <Metric label="Hard rejected" value={stats?.rejected} />
      </dl>

      <nav className="mt-6 flex gap-4 border-b border-slate-200 text-sm">
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => {
              setTab(item.key)
              setOffset(0)
            }}
            className={`-mb-px border-b-2 pb-2 ${
              tab === item.key
                ? 'border-slate-900 font-medium text-slate-900'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="mt-4 flex flex-wrap gap-2 text-sm">
        <input
          value={search}
          onChange={(event) => {
            setSearch(event.target.value)
            setOffset(0)
          }}
          placeholder="Search title or company…"
          aria-label="Search jobs"
          className="min-w-56 flex-1 border border-slate-300 px-2 py-1.5"
        />
        <select
          value={postedWithin}
          onChange={(event) => setPostedWithin(event.target.value)}
          aria-label="Posted within"
          className="border border-slate-300 px-2 py-1.5"
        >
          <option value="">Any posting date</option>
          <option value="24">Last 24 hours</option>
          <option value="48">Last 48 hours</option>
          <option value="72">Last 72 hours</option>
        </select>
        <select
          value={workplace}
          onChange={(event) => setWorkplace(event.target.value)}
          aria-label="Workplace type"
          className="border border-slate-300 px-2 py-1.5"
        >
          <option value="">Any workplace</option>
          <option value="Remote">Remote</option>
          <option value="Hybrid">Hybrid</option>
          <option value="Onsite">On-site</option>
        </select>
        <select
          value={sort}
          onChange={(event) => setSort(event.target.value)}
          aria-label="Sort order"
          className="border border-slate-300 px-2 py-1.5"
        >
          <option value="newest">Newest</option>
          <option value="company">Company</option>
          <option value="salary">Salary</option>
        </select>
      </div>

      {error && (
        <p className="mt-4 border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      <table className="mt-4 w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
            <th className="pb-2 font-medium">Role</th>
            <th className="pb-2 font-medium">Company</th>
            <th className="pb-2 font-medium">Posted</th>
            <th className="pb-2 font-medium">Status</th>
            <th className="pb-2 text-right font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <JobRow key={job.id} job={job} onStatusChange={onStatusChange} />
          ))}
        </tbody>
      </table>

      {jobs.length === 0 && !error && (
        <p className="mt-6 text-sm text-slate-500">
          No jobs match these filters. Configure a source board and run discovery.
        </p>
      )}

      <div className="mt-4 flex items-center justify-between text-xs text-slate-600">
        <span>
          {total === 0 ? '0' : `${offset + 1}–${Math.min(offset + PAGE_SIZE, total)}`} of {total}
        </span>
        <span className="flex gap-2">
          <button
            type="button"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            className="border border-slate-300 px-2 py-1 disabled:opacity-40"
          >
            Previous
          </button>
          <button
            type="button"
            disabled={offset + PAGE_SIZE >= total}
            onClick={() => setOffset(offset + PAGE_SIZE)}
            className="border border-slate-300 px-2 py-1 disabled:opacity-40"
          >
            Next
          </button>
        </span>
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value?: number }) {
  return (
    <div className="bg-white px-4 py-3">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="text-xl font-semibold tabular-nums">{value ?? '—'}</dd>
    </div>
  )
}
