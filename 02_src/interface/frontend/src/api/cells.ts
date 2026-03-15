import { apiFetch } from './client'
import type { MatrixView, CellContent, CellParameters } from './types'

export function fetchMatrix(
  cellId: string,
  nameRu: string,
  venueKey: string,
): Promise<MatrixView> {
  const params = new URLSearchParams({ name_ru: nameRu, venue_key: venueKey })
  return apiFetch<MatrixView>(`/cells/${encodeURIComponent(cellId)}/matrix?${params}`)
}

export function fetchCellContent(
  cellId: string,
  nameRu: string,
  venueKey: string,
): Promise<CellContent> {
  const params = new URLSearchParams({ name_ru: nameRu, venue_key: venueKey })
  return apiFetch<CellContent>(`/cells/${encodeURIComponent(cellId)}/content?${params}`)
}

export function fetchCellParameters(
  cellId: string,
  nameRu: string,
  venueKey: string,
): Promise<CellParameters> {
  const params = new URLSearchParams({ name_ru: nameRu, venue_key: venueKey })
  return apiFetch<CellParameters>(`/cells/${encodeURIComponent(cellId)}/parameters?${params}`)
}
