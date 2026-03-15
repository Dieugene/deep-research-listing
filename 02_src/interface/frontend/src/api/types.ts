// ============================================================
// API Types — Listing Requirements Database
// ============================================================

export type ValidationStatus = 'green' | 'yellow' | 'red' | 'unknown'
export type MatrixCellStatus = 'filled' | 'not_filled' | 'not_applicable'

// ---- Jurisdictions ----

export interface JurisdictionSummary {
  name_ru: string
  name_en: string
  legal_family: string | null
  venue_count: number
  has_level4: boolean
  has_full_data: boolean
  iso_code: string | null        // ISO 3166-1 alpha-2, e.g. "GB", "HK"
  market_type: string | null     // "DM" | "EM" (MSCI classification)
  data_status: string            // "full" | "partial" | "empty"
  listing_authority: string | null  // e.g. "FCA", "SFC", "ASIC"
}

export interface VenueInJurisdiction {
  venue_key: string
  name: string
  name_ru: string
  venue_type: string
  cell_count: number
}

export interface Level4Item {
  description_ru?: string
  description?: string
  period?: string
  year?: string
  source?: string
  [key: string]: unknown
}

export interface Level4Data {
  problems: Level4Item[]
  contradictions: Level4Item[]
  parameters_as_tools: Level4Item[]
  reforms: Level4Item[]
  validation_status: string
}

export interface JurisdictionCard {
  name_ru: string
  name_en: string
  legal_family: string | null
  regulator_name: string | null
  regulator_type: string | null
  admission_architecture: string | null
  admission_architecture_ru: string | null
  listing_authority: string | null
  iso_code: string | null
  data_status: string
  market_types: string[]
  key_terms_mapping: Record<string, string>
  supranational_flag: boolean
  supranational_framework: string | null
  notes: string | null
  notes_ru: string | null
  venues: VenueInJurisdiction[]
  level4: Level4Data | null
}

// ---- Venues ----

export interface CellInVenue {
  cell_id: string
  tier: string
  instrument_class_key: string
  instrument_class_label: string
  has_admission_data: boolean
  has_maintenance_data: boolean
  has_enforcement_data: boolean
  has_parameters: boolean
  validation_status: ValidationStatus
}

export interface VenueCard {
  venue_key: string
  venue_name_english: string
  venue_name_local: string | null
  venue_name_ru: string | null
  jurisdiction_ru: string
  jurisdiction_en: string | null
  venue_type: string
  operator: string | null
  secondary_listing_regime: boolean
  listing_architecture: string | null
  tiers: Record<string, unknown>[]
  segments: Record<string, unknown>[]
  instrument_coverage: Record<string, unknown>[]
  notes: string | null
  notes_ru: string | null
  cells: CellInVenue[]
}

// ---- Matrix ----

export interface MatrixColumn {
  col_index: number
  col_key: string
  col_label: string
  status: MatrixCellStatus
  text_volume: number
}

export interface MatrixRow {
  row_index: number
  row_key: string
  row_label: string
  columns: MatrixColumn[]
}

export interface MatrixView {
  cell_id: string
  venue_key: string
  tier: string
  instrument_class_key: string
  instrument_class_label: string
  validation_status: ValidationStatus
  rows: MatrixRow[]
}

// ---- Cell Content ----

export interface ContentSection {
  section_key: string
  section_label: string
  text: string
  source: string | null
}

export interface PhaseContent {
  phase_key: string
  phase_label: string
  has_data: boolean
  validation_status: ValidationStatus
  sections: ContentSection[]
}

export interface CellContent {
  cell_id: string
  venue_key: string
  tier: string
  instrument_class_key: string
  instrument_class_label: string
  phases: PhaseContent[]
}

// ---- Parameters ----

export interface ParameterValue {
  parameter_id: string
  parameter_name: string
  lifecycle_phase_key: string
  lifecycle_phase_label: string
  value: string
  calculation_methodology: string | null
  alternatives: string | null
  variations: string | null
  linkages: string[]
  source: string | null
  status: string
  status_label: string
  drill_down_applied: boolean
  note: string | null
}

export interface CellParameters {
  cell_id: string
  venue_key: string
  tier: string
  instrument_class_label: string
  parameters: ParameterValue[]
}

export interface ParameterSummary {
  parameter_id: string
  parameter_name: string
  occurrence_count: number
}

export interface ParameterComparisonEntry {
  jurisdiction_ru: string
  venue_key: string
  venue_name: string
  cell_id: string
  tier: string
  instrument_class_key: string
  instrument_class_label: string
  lifecycle_phase_key: string
  lifecycle_phase_label: string
  value: string
  source: string | null
}

export interface ParameterComparison {
  parameter_id: string
  parameter_name: string
  entries: ParameterComparisonEntry[]
}
