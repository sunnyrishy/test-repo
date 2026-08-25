/** Renders a real relative posting time, or says the date is unavailable.
 *  It never falls back to the time we first saw the job. */
export default function PostedAt({
  postedAt,
  freshness,
  maxAgeHours = 72,
}: {
  postedAt: string | null
  freshness: string
  maxAgeHours?: number
}) {
  if (!postedAt) {
    return <span className="text-slate-400">Posted date unavailable</span>
  }
  const ageHours = (Date.now() - new Date(postedAt).getTime()) / 3_600_000
  const label =
    ageHours < 1
      ? 'Posted less than an hour ago'
      : ageHours < 24
        ? `Posted ${Math.floor(ageHours)}h ago`
        : `Posted ${Math.floor(ageHours / 24)}d ago`

  const remaining = maxAgeHours - ageHours
  return (
    <span>
      {label}
      {freshness === 'FRESH' && remaining <= 12 && (
        <span className="ml-2 text-amber-700">
          ⚠ {Math.max(0, Math.floor(remaining))}h left in freshness window
        </span>
      )}
    </span>
  )
}
