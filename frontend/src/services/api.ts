import type { JobDetail, JobPage, Stats } from '../types/job'

const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`)
  }
  return (await response.json()) as T
}

export interface JobQuery {
  search?: string
  status?: string
  filter_status?: string
  workplace_type?: string
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

export const runDiscovery = () =>
  request<Record<string, unknown>>('/api/admin/discovery/run', { method: 'POST' })
