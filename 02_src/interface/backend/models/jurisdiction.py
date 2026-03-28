"""
Pydantic models for jurisdiction-level API responses.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class InstitutionalMetric(BaseModel):
    value: float | None = None
    year: int | None = None
    percentile: int | None = None


class InvestorProtection(BaseModel):
    disclosure: float | None = None
    director_liability: float | None = None
    shareholder_suits: float | None = None
    composite: float | None = None


class InstitutionalMetrics(BaseModel):
    rule_of_law: InstitutionalMetric | None = None
    regulatory_quality: InstitutionalMetric | None = None
    political_stability: InstitutionalMetric | None = None
    wgi_composite: InstitutionalMetric | None = None
    market_cap_gdp_pct: InstitutionalMetric | None = None
    investor_protection: InvestorProtection | None = None


class SimilarJurisdiction(BaseModel):
    iso_code: str
    name_en: str
    name_ru: str | None = None
    score: float | None = None
    common_traits: list[str] = []


class JurisdictionSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name_ru: str
    name_en: str
    legal_family: str | None
    venue_count: int
    has_level4: bool
    has_full_data: bool  # True if L1 + L2 + L3 all exist
    iso_code: str | None = None          # ISO 3166-1 alpha-2, e.g. "GB", "HK"
    market_type: str | None = None       # MSCI classification: "DM" | "EM"
    data_status: str = "empty"           # "full" | "partial" | "empty"
    listing_authority: str | None = None  # e.g. "FCA", "SFC", "ASIC"


class VenueInJurisdiction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    venue_key: str
    name: str        # venue_name_english
    name_ru: str
    venue_type: str  # human-readable from VENUE_TYPE_LABELS
    cell_count: int
    research_priority: str = "primary"


class Level4Data(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    problems: list[dict]
    contradictions: list[dict]
    parameters_as_tools: list[dict]
    reforms: list[dict]
    validation_status: str
    sources: list[dict] | None = None


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
    listing_authority_short: str | None = None
    iso_code: str | None = None           # ISO 3166-1 alpha-2, e.g. "GB", "HK"
    market_type: str | None = None        # MSCI classification: "DM" | "EM"
    data_status: str = "empty"            # "full" | "partial" | "empty"
    market_types: list[str] = []
    key_terms_mapping: dict = {}
    supranational_flag: bool = False
    supranational_framework: str | None
    notes: str | None
    notes_ru: str | None = None
    sources: list[dict] | None = None
    institutional_metrics: InstitutionalMetrics | None = None
    cluster_label: str | None = None
    similar_jurisdictions: list[SimilarJurisdiction] = []
    venues: list[VenueInJurisdiction]
    level4: Level4Data | None
