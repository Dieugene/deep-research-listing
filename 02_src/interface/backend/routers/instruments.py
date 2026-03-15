"""
Instrument comparison API endpoints.
"""
from fastapi import APIRouter, Depends, Query

from dependencies import get_repository
from models.instrument import InstrumentComparison, InstrumentSummary
from repositories.file_repo import FileDataRepository

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("/", response_model=list[InstrumentSummary])
def list_instruments(repo: FileDataRepository = Depends(get_repository)):
    """Return summary for all instrument classes."""
    return repo.get_instrument_summaries()


@router.get("/{instrument_class_key}/comparison", response_model=InstrumentComparison)
def get_comparison(
    instrument_class_key: str,
    phase: str = Query(default="admission"),
    repo: FileDataRepository = Depends(get_repository),
):
    """Return comparison data for an instrument class and phase."""
    return repo.get_instrument_comparison(instrument_class_key, phase)
