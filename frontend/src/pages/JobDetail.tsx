import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import PostedAt from '../components/PostedAt'
import { fetchJob } from '../services/api'
import type { JobDetail as JobDetailType } from '../types/job'

export default function JobDetail() {
  const { id } = useParams<{ id: string }>()
  const [job, setJob] = useState<JobDetailType | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    fetchJob(id)
      .then(setJob)
      .catch((err: Error) => setError(err.message))
  }, [id])

  if (error) return <p className="text-sm text-red-800">{error}</p>
  if (!job) return <p className="text-sm text-slate-500">Loading…</p>

  return (
    <article>
      <Link to="/" className="text-xs text-slate-500 underline-offset-2 hover:underline">
        ← Back to dashboard
      </Link>

      <h1 className="mt-3 text-xl font-semibold">{job.title}</h1>
      <p className="text-slate-700">{job.company}</p>

      <dl className="mt-4 grid grid-cols-2 gap-x-8 gap-y-2 text-sm sm:grid-cols-3">
        <Field label="Location" value={job.location ?? 'Not stated'} />
        <Field label="Workplace" value={job.workplace_type ?? 'Unknown'} />
        <Field label="Employment" value={job.employment_type ?? 'Unknown'} />
        <Field
          label="Posted"
          value={<PostedAt postedAt={job.posted_at} freshness={job.freshness_status} />}
        />
        <Field
          label="Salary"
          value={
            job.salary_min || job.salary_max
              ? `${job.salary_min ?? '?'}–${job.salary_max ?? '?'} ${job.currency ?? ''}`
              : 'Not published'
          }
        />
        <Field
          label="Deterministic filter"
          value={
            job.filter_status === 'PASS'
              ? '✓ Passed'
              : `✕ Rejected — ${job.filter_rejection_reason ?? 'unknown reason'}`
          }
        />
      </dl>

      <section className="mt-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Sources</h2>
        <ul className="mt-2 space-y-1 text-sm">
          {job.sources.map((source) => (
            <li key={source.source}>
              <span className="text-slate-500">{source.source}: </span>
              {source.source_url ? (
                <a
                  href={source.source_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="text-blue-700 underline-offset-2 hover:underline"
                >
                  {source.source_url}
                </a>
              ) : (
                <span className="text-slate-400">no link</span>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Description
        </h2>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-800">
          {job.description ?? 'The source did not provide a description.'}
        </p>
      </section>

      {job.application_url && (
        <a
          href={job.application_url}
          target="_blank"
          rel="noreferrer noopener"
          className="mt-8 inline-block bg-slate-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-slate-800"
        >
          APPLY ON COMPANY WEBSITE →
        </a>
      )}
    </article>
  )
}

function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="text-slate-900">{value}</dd>
    </div>
  )
}
