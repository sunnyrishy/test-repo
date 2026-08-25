export interface JobSource {
  source: string
  source_url: string | null
  application_url: string | null
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
  passed_filters: number
  rejected: number
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
    errors: string | null
  }
}
