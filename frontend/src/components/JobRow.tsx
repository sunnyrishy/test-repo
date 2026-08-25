import { Link } from 'react-router-dom'
import type { Job } from '../types/job'
import PostedAt from './PostedAt'
import ScoreBadge from './ScoreBadge'

const STATUS_LABELS: Record<string, string> = {
  NEW: 'New',
  SAVED: 'Saved',
  APPLIED: 'Applied',
  INTERVIEW: 'Interview',
  REJECTED: 'Rejected',
  CLOSED: 'Closed',
}

export default function JobRow({
  job,
  onStatusChange,
}: {
  job: Job
  onStatusChange: (id: number, status: string) => void
}) {
  return (
    <tr className="border-t border-slate-200 align-top hover:bg-slate-50">
      <td className="py-3 pr-3 whitespace-nowrap">
        <ScoreBadge score={job.score} />
      </td>
      <td className="py-3 pr-4">
        <Link to={`/job/${job.id}`} className="font-medium text-slate-900 hover:underline">
          {job.title}
        </Link>
        <div className="text-xs text-slate-500">
          {job.location ?? 'Location not stated'}
          {job.workplace_type && job.workplace_type !== 'Unknown' && ` · ${job.workplace_type}`}
        </div>
      </td>
      <td className="py-3 pr-4 text-slate-700">{job.company}</td>
      <td className="py-3 pr-4 text-xs text-slate-600">
        <PostedAt postedAt={job.posted_at} freshness={job.freshness_status} />
      </td>
      <td className="py-3 pr-4 text-xs text-slate-600">{STATUS_LABELS[job.status] ?? job.status}</td>
      <td className="py-3 text-right text-xs">
        <button
          type="button"
          onClick={() => onStatusChange(job.id, job.status === 'SAVED' ? 'NEW' : 'SAVED')}
          className="mr-3 text-slate-600 underline-offset-2 hover:underline"
        >
          {job.status === 'SAVED' ? 'Unsave' : 'Save'}
        </button>
        <button
          type="button"
          onClick={() => onStatusChange(job.id, 'APPLIED')}
          className="mr-3 text-slate-600 underline-offset-2 hover:underline"
        >
          Mark applied
        </button>
        {job.application_url ? (
          <a
            href={job.application_url}
            target="_blank"
            rel="noreferrer noopener"
            className="font-medium text-blue-700 underline-offset-2 hover:underline"
          >
            Apply →
          </a>
        ) : (
          <span className="text-slate-400">No application link</span>
        )}
      </td>
    </tr>
  )
}
