"""
Pydantic models for cell-level API responses (matrix and content views).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from models.common import MatrixCellStatus


class MatrixColumn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    col_index: int       # 1–5
    col_key: str         # "requirements" | "procedures" | "monitoring" | "sanctions" | "disclosure"
    col_label: str       # from CONTENT_TYPE_LABELS
    status: MatrixCellStatus
    text_volume: int = 0  # character count of underlying raw JSON (for UI colour intensity)
    snippet: str | None = None  # First ~150 chars of content for micro-excerpt display
    snippet_hint: str | None = None  # Section subtitle(s) for source hint


class MatrixRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    row_index: int   # 1–4
    row_key: str     # "admission" | "continuing" | "suspension" | "delisting"
    row_label: str   # from LIFECYCLE_PHASE_LABELS
    columns: list[MatrixColumn]


class MatrixView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cell_id: str
    venue_key: str
    tier: str
    tier_ru: str | None = None
    instrument_class_key: str
    instrument_class_label: str
    validation_status: str
    rows: list[MatrixRow]


class ContentSection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    section_key: str
    section_label: str
    text: str
    source: str | None = None
    citations: list[dict] = []  # [{url, title, field?}] — filtered from raw file's citations array


class PhaseContent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    phase_key: str
    phase_label: str
    has_data: bool
    validation_status: str
    sections: list[ContentSection]
    citations: list[dict] = []  # Phase-level citations from _parallel_raw


class CellContent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cell_id: str
    venue_key: str
    tier: str
    tier_ru: str | None = None
    instrument_class_key: str
    instrument_class_label: str
    phases: list[PhaseContent]  # 3 phases: admission, maintenance, enforcement
