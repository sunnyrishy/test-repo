export interface JobSource {
  source: string
  source_url: string | null
  application_url: string | null
}

export interface Score {
  overall_score: number
  classification: 'EXCELLENT' | 'VERY_STRONG' | 'STRONG' | 'CONSIDER' | 'BELOW_THRESHOLD'
  role_score: number
  experience_score: number
  skill_score: number
  degree_score: number
  graduation_score: number
  work_auth_score: number
  location_score: number
  salary_score: number
  company_score: number
}

export interface Verification {
  decision: 'PASS' | 'FAIL' | 'REVIEW' | 'ERROR'
  confidence: number
  role_match: boolean | null
  entry_level: boolean | null
  experience_match: boolean | null
  degree_match: boolean | null
  graduation_match: boolean | null
  location_match: boolean | null
  employment_match: boolean | null
  citizenship_required: boolean | null
  security_clearance_required: boolean | null
  experience_required: number | null
  experience_type: string | null
  education_required: string | null
  work_authorization_status: string
  sponsorship_status: string
  matched_skills: string[]
  missing_skills: string[]
  rejection_reasons: string[]
  ai_summary: string | null
  model: string | null
}

export interface Job {
  id: number
  source: string
  company: string
  title: string
  location: string | null
  country: string | null
  workplace_type: string | null
  employment_type: string | null
  application_url: string | null
  source_url: string | null
  posted_at: string | null
  first_seen_at: string
  freshness_status: 'FRESH' | 'STALE' | 'UNKNOWN'
  salary_min: number | null
  salary_max: number | null
  currency: string | null
  filter_status: 'PENDING' | 'PASS' | 'REJECT'
  filter_rejection_reason: string | null
  status: string
  sources: JobSource[]
  score: Score | null
  verification: Verification | null
}

export interface JobDetail extends Job {
  description: string | null
}

export interface JobPage {
  items: Job[]
  total: number
  limit: number
  offset: number
}

export interface Stats {
  discovered_today: number
  discovered_this_week: number
  duplicates_merged: number
  passed_filters: number
  rejected: number
  verified: number
  verified_pass: number
  verified_fail: number
  verified_review: number
  verification_errors: number
  average_score: number | null
  excellent_matches: number
  min_match_score: number
  by_classification: Record<string, number>
  by_rejection_reason: Record<string, number>
  by_source: Record<string, number>
  last_run: null | {
    started_at: string
    finished_at: string | null
    discovered: number
    duplicates: number
    stored: number
    hard_filter_failures: number
    passed_filters: number
    per_source: string | null
    errors: string | null
  }
}
