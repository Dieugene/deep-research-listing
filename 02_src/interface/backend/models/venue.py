"""
Pydantic models for venue-level API responses.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CellInVenue(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cell_id: str
    tier: str
    instrument_class_key: str    # "equity", "bond", etc. (for frontend filters)
    instrument_class_label: str  # "Акции", etc.
    has_admission_data: bool
    has_maintenance_data: bool
    has_enforcement_data: bool
    has_parameters: bool
    validation_status: str       # from ValidationStatus enum values


class VenueCard(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    venue_key: str
    venue_name_english: str
    venue_name_local: str | None
    venue_name_ru: str | None
    jurisdiction_ru: str
    jurisdiction_en: str | None
    venue_type: str                  # human-readable from VENUE_TYPE_LABELS
    operator: str | None
    secondary_listing_regime: bool
    listing_architecture: str | None
    tiers: list[dict]
    segments: list[dict]
    instrument_coverage: list[dict]
    notes: str | None
    notes_ru: str | None
    cells: list[CellInVenue]
