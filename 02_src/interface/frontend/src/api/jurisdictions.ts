import { apiFetch } from './client'
import type { JurisdictionSummary, JurisdictionCard } from './types'

export function fetchJurisdictions(): Promise<JurisdictionSummary[]> {
  return apiFetch<JurisdictionSummary[]>('/jurisdictions/')
}

export function fetchJurisdiction(nameRu: string): Promise<JurisdictionCard> {
  return apiFetch<JurisdictionCard>(`/jurisdictions/${encodeURIComponent(nameRu)}`)
}
