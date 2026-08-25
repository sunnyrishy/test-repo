import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import PostedAt from '../components/PostedAt'
import ScoreBadge from '../components/ScoreBadge'
import VerificationPanel from '../components/VerificationPanel'
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

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold">{job.title}</h1>
        <ScoreBadge score={job.score} />
      </div>
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
          label="Filter"
          value={
            job.filter_status === 'PASS'
              ? '✓ Passed'
              : `✕ Rejected — ${job.filter_rejection_reason ?? 'unknown reason'}`
          }
        />
      </dl>

      <section className="mt-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Verification
        </h2>
        <div className="mt-2">
          <VerificationPanel verification={job.verification} />
        </div>
      </section>

      {job.score && (
        <section className="mt-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Score breakdown
          </h2>
          <ul className="mt-2 grid gap-x-8 text-sm sm:grid-cols-2">
            {[
              ['Role relevance', job.score.role_score, 20],
              ['Entry-level fit', job.score.experience_score, 20],
              ['Technical skills', job.score.skill_score, 15],
              ['Degree', job.score.degree_score, 10],
              ['Graduation year', job.score.graduation_score, 10],
              ['Work authorization', job.score.work_auth_score, 10],
              ['Location', job.score.location_score, 5],
              ['Salary', job.score.salary_score, 5],
              ['Posting quality', job.score.company_score, 5],
            ].map(([label, value, max]) => (
              <li key={label as string} className="flex justify-between border-b border-slate-100 py-1">
                <span className="text-slate-600">{label as string}</span>
                <span className="tabular-nums">
                  {(value as number).toFixed(1)} / {max as number}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

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
