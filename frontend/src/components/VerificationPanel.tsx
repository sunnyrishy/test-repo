import type { Verification } from '../types/job'

const CHECKS: { key: keyof Verification; label: string; invert?: boolean }[] = [
  { key: 'role_match', label: 'Role match' },
  { key: 'entry_level', label: 'Entry level' },
  { key: 'experience_match', label: 'Experience' },
  { key: 'degree_match', label: 'Degree' },
  { key: 'graduation_match', label: 'Graduation year' },
  { key: 'location_match', label: 'Location' },
  { key: 'employment_match', label: 'Employment type' },
  { key: 'citizenship_required', label: 'Citizenship required', invert: true },
  { key: 'security_clearance_required', label: 'Clearance required', invert: true },
]

/** null means the model could not determine it — shown as unknown, never as a
 *  pass. */
function mark(value: boolean | null, invert: boolean) {
  if (value === null || value === undefined) return { icon: '?', text: 'Unknown', className: 'text-amber-700' }
  const good = invert ? !value : value
  return good
    ? { icon: '✓', text: invert ? 'No' : 'Yes', className: 'text-emerald-700' }
    : { icon: '✕', text: invert ? 'Yes' : 'No', className: 'text-red-700' }
}

const STATUS_LABELS: Record<string, string> = {
  CLEARLY_COMPATIBLE: 'Clearly compatible',
  PROBABLY_COMPATIBLE: 'Probably compatible',
  UNKNOWN: 'Not specified',
  PROBABLY_INCOMPATIBLE: 'Probably incompatible',
  CLEARLY_INCOMPATIBLE: 'Clearly incompatible',
  AVAILABLE: 'Available',
  POSSIBLY_AVAILABLE: 'Possibly available',
  NOT_SPECIFIED: 'Not specified',
  NOT_AVAILABLE: 'Not available',
  REQUIRES_CITIZENSHIP: 'Requires citizenship',
}

export default function VerificationPanel({ verification }: { verification: Verification | null }) {
  if (!verification) {
    return <p className="text-sm text-slate-500">This job has not been verified yet.</p>
  }

  return (
    <div>
      <p className="text-sm text-slate-800">
        <span className="font-medium">{verification.decision}</span>{' '}
        <span className="text-slate-500">
          (confidence {(verification.confidence * 100).toFixed(0)}%
          {verification.model && `, model ${verification.model}`})
        </span>
      </p>

      {verification.ai_summary && (
        <p className="mt-2 text-sm leading-6 text-slate-700">{verification.ai_summary}</p>
      )}

      <ul className="mt-3 grid gap-x-8 gap-y-1 text-sm sm:grid-cols-2">
        {CHECKS.map(({ key, label, invert }) => {
          const state = mark(verification[key] as boolean | null, invert ?? false)
          return (
            <li key={key} className="flex justify-between border-b border-slate-100 py-1">
              <span className="text-slate-600">{label}</span>
              <span className={state.className}>
                <span aria-hidden="true">{state.icon}</span> {state.text}
              </span>
            </li>
          )
        })}
      </ul>

      <dl className="mt-4 grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs text-slate-500">Experience required</dt>
          <dd>
            {verification.experience_required === null
              ? 'Not stated'
              : `${verification.experience_required} years (${verification.experience_type ?? 'unspecified'})`}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Education required</dt>
          <dd>{verification.education_required ?? 'Not stated'}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Work authorization</dt>
          <dd>
            {STATUS_LABELS[verification.work_authorization_status] ??
              verification.work_authorization_status}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Sponsorship</dt>
          <dd>{STATUS_LABELS[verification.sponsorship_status] ?? verification.sponsorship_status}</dd>
        </div>
      </dl>

      {verification.matched_skills.length > 0 && (
        <p className="mt-4 text-sm">
          <span className="text-xs text-slate-500">Matched skills: </span>
          {verification.matched_skills.join(' · ')}
        </p>
      )}
      {verification.rejection_reasons.length > 0 && (
        <ul className="mt-3 list-inside list-disc text-sm text-red-800">
          {verification.rejection_reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
