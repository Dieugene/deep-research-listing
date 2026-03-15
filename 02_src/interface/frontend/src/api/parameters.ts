import { apiFetch } from './client'
import type { ParameterSummary, ParameterComparison } from './types'

export function fetchParameters(): Promise<ParameterSummary[]> {
  return apiFetch<ParameterSummary[]>('/parameters/')
}

export function fetchParameter(parameterId: string): Promise<ParameterComparison> {
  return apiFetch<ParameterComparison>(`/parameters/${encodeURIComponent(parameterId)}`)
}
