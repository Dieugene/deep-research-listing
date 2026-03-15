import { apiFetch } from './client'
import type { VenueCard } from './types'

export function fetchVenue(venueKey: string): Promise<VenueCard> {
  return apiFetch<VenueCard>(`/venues/${encodeURIComponent(venueKey)}`)
}
