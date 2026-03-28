"""
Pydantic models for parameter-level API responses.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ParameterValue(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    parameter_id: str                # e.g. "П01"
    parameter_name: str
    lifecycle_phase_key: str
    lifecycle_phase_label: str
    value: str
    calculation_methodology: str | None
    alternatives: str | None
    variations: str | None
    linkages: list[str]
    source: str | None
    status: str                      # "found" | "not_found" | "not_applicable"
    status_label: str
    drill_down_applied: bool = False
    note: str | None
    section_keys: list[str] = []


class CellParameters(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cell_id: str
    venue_key: str
    tier: str
    tier_ru: str | None = None
    instrument_class_label: str
    parameters: list[ParameterValue]


class ParameterSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    parameter_id: str
    parameter_name: str
    occurrence_count: int  # number of cells that have this parameter with status "found"


class ParameterComparisonEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    jurisdiction_ru: str
    venue_key: str
    venue_name: str
    cell_id: str
    tier: str
    instrument_class_key: str
    instrument_class_label: str
    lifecycle_phase_key: str
    lifecycle_phase_label: str
    value: str
    source: str | None


class ParameterComparison(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    parameter_id: str
    parameter_name: str
    entries: list[ParameterComparisonEntry]
