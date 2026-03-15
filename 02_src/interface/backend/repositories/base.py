"""
DataRepository Protocol — defines the interface all repository implementations must satisfy.
"""
from __future__ import annotations

from typing import Protocol

from models.jurisdiction import JurisdictionSummary, JurisdictionCard
from models.venue import VenueCard
from models.cell import MatrixView, CellContent
from models.parameter import CellParameters, ParameterSummary, ParameterComparison
from models.instrument import InstrumentSummary, InstrumentComparison


class DataRepository(Protocol):
    def get_jurisdictions(self) -> list[JurisdictionSummary]: ...

    def get_jurisdiction(self, name_ru: str) -> JurisdictionCard | None: ...

    def get_venue(self, venue_key: str) -> VenueCard | None: ...

    def get_cell_matrix(
        self, name_ru: str, venue_key: str, cell_id: str
    ) -> MatrixView | None: ...

    def get_cell_content(
        self, name_ru: str, venue_key: str, cell_id: str
    ) -> CellContent | None: ...

    def get_cell_parameters(
        self, name_ru: str, venue_key: str, cell_id: str
    ) -> CellParameters | None: ...

    def get_all_parameters(self) -> list[ParameterSummary]: ...

    def get_parameter_comparison(
        self, parameter_id: str
    ) -> ParameterComparison | None: ...

    def get_instrument_summaries(self) -> list[InstrumentSummary]: ...

    def get_instrument_comparison(
        self, instrument_class_key: str, phase_key: str
    ) -> InstrumentComparison: ...
