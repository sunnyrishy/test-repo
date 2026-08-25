import type { JobDetail, JobPage, Stats } from '../types/job'

const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const API_KEY_STORAGE = 'aji.apiKey'

/** The admin key is typed in by the user and kept in this browser only. It is
 *  deliberately NOT a build-time variable: anything baked into the bundle is
 *  public, and this key can trigger model spend. */
export function getApiKey(): string {
  try {
    return localStorage.getItem(API_KEY_STORAGE) ?? ''
  } catch {
    return ''
  }
}

export function setApiKey(value: string): void {
  try {
    if (value) localStorage.setItem(API_KEY_STORAGE, value)
    else localStorage.removeItem(API_KEY_STORAGE)
  } catch {
    /* private browsing: the key simply is not remembered */
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const key = getApiKey()
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...(init?.headers ?? {}), ...(key ? { 'X-API-Key': key } : {}) },
  })
  if (response.status === 401) {
    throw new Error('Unauthorized — set the admin key to run pipeline actions')
  }
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`)
  }
  return (await response.json()) as T
}

export interface JobQuery {
  search?: string
  status?: string
  view?: string
  min_score?: number
  workplace_type?: string
  work_authorization?: string
  sponsorship?: string
  min_salary?: number
  posted_within_hours?: number
  sort?: string
  limit?: number
  offset?: number
}

export function fetchJobs(query: JobQuery): Promise<JobPage> {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== '') params.set(key, String(value))
  }
  return request<JobPage>(`/api/jobs?${params.toString()}`)
}

export const fetchJob = (id: string) => request<JobDetail>(`/api/jobs/${id}`)

export const fetchStats = () => request<Stats>('/api/jobs/stats')

export const setJobStatus = (id: number, status: string) =>
  request<{ id: number; status: string }>(`/api/jobs/${id}/status?status=${status}`, {
    method: 'POST',
  })

export const runPipeline = () =>
  request<Record<string, unknown>>('/api/admin/pipeline/run', { method: 'POST' })
