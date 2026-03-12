"""
Pydantic models for jurisdiction-level API responses.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class JurisdictionSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name_ru: str
    name_en: str
    legal_family: str | None
    venue_count: int
    has_level4: bool
    has_full_data: bool  # True if L1 + L2 + L3 all exist


class VenueInJurisdiction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    venue_key: str
    name: str        # venue_name_english
    name_ru: str
    venue_type: str  # human-readable from VENUE_TYPE_LABELS
    cell_count: int


class Level4Data(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    problems: list[dict]
    contradictions: list[dict]
    parameters_as_tools: list[dict]
    reforms: list[dict]
    validation_status: str


class JurisdictionCard(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name_ru: str
    name_en: str
    legal_family: str | None
    regulator_name: str | None
    regulator_type: str | None
    admission_architecture: str | None
    admission_architecture_ru: str | None
    listing_authority: str | None
    market_types: list[str]
    key_terms_mapping: dict
    supranational_flag: bool
    supranational_framework: str | None
    notes: str | None
    venues: list[VenueInJurisdiction]
    level4: Level4Data | None
