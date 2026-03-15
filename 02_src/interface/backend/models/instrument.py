"""
Pydantic models for instrument comparison API responses.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from models.parameter import ParameterSummary


class InstrumentSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    instrument_class_key: str        # "equity", "bond", "fund", "depositary_receipt"
    instrument_class_label: str      # "Акции", "Облигации", "Фонды", "Депозитарные расписки"
    regime_count: int                # total number of listing regimes with parameters
    top_parameters: list[ParameterSummary]   # top 5 by occurrence in this instrument


class InstrumentRegime(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cell_id: str
    venue_key: str
    venue_name: str
    venue_type: str
    jurisdiction_ru: str
    legal_family: str | None
    tier: str
    validation_status: str           # "green" | "yellow" | "red" | "unknown"
    parameter_values: dict[str, str] # parameter_id → value (for the requested phase)


class InstrumentComparison(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    instrument_class_key: str
    instrument_class_label: str
    phase_key: str
    phase_label: str
    parameters: list[ParameterSummary]   # available parameters sorted by occurrence_count desc
    regimes: list[InstrumentRegime]
