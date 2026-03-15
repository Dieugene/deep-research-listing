import { apiFetch } from './client'
import type { InstrumentSummary, InstrumentComparison } from './types'

export function fetchInstrumentSummaries(): Promise<InstrumentSummary[]> {
  return apiFetch<InstrumentSummary[]>('/instruments/')
}

export function fetchInstrumentComparison(
  instrumentClassKey: string,
  phase: string,
): Promise<InstrumentComparison> {
  return apiFetch<InstrumentComparison>(
    `/instruments/${encodeURIComponent(instrumentClassKey)}/comparison?phase=${encodeURIComponent(phase)}`,
  )
}
