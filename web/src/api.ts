import type { Payload } from './types'

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(body?.error ?? `Server ${response.status} cavabı verdi`)
  }
  return body as T
}

export const loadData = () => request<Payload>('/api/data')

export const refreshData = () =>
  request<{ recent: boolean; sentry: boolean; close_approach: boolean }>('/api/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  })
