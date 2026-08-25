import type { Score } from '../types/job'

/** Colour is never the only signal: the number and a word carry the meaning. */
const STYLES: Record<string, { label: string; className: string }> = {
  EXCELLENT: { label: 'Excellent', className: 'bg-emerald-50 text-emerald-900 border-emerald-300' },
  VERY_STRONG: { label: 'Very strong', className: 'bg-emerald-50 text-emerald-800 border-emerald-200' },
  STRONG: { label: 'Strong', className: 'bg-blue-50 text-blue-900 border-blue-200' },
  CONSIDER: { label: 'Consider', className: 'bg-amber-50 text-amber-900 border-amber-300' },
  BELOW_THRESHOLD: { label: 'Below threshold', className: 'bg-slate-50 text-slate-700 border-slate-300' },
}

export default function ScoreBadge({ score }: { score: Score | null }) {
  if (!score) {
    return <span className="text-xs text-slate-400">Not scored</span>
  }
  const style = STYLES[score.classification] ?? STYLES.BELOW_THRESHOLD
  return (
    <span
      className={`inline-flex items-baseline gap-1.5 border px-1.5 py-0.5 text-xs ${style.className}`}
      title={`${score.overall_score.toFixed(0)}/100 — ${style.label}`}
    >
      <span className="font-semibold tabular-nums">{score.overall_score.toFixed(0)}</span>
      <span>{style.label}</span>
    </span>
  )
}
