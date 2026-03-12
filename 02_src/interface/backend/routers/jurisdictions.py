"""
Jurisdiction-level API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_repository
from models.jurisdiction import JurisdictionCard, JurisdictionSummary
from repositories.file_repo import FileDataRepository

router = APIRouter(prefix="/jurisdictions", tags=["jurisdictions"])


@router.get("/", response_model=list[JurisdictionSummary])
def list_jurisdictions(repo: FileDataRepository = Depends(get_repository)):
    """Return a summary list of all available jurisdictions."""
    return repo.get_jurisdictions()


@router.get("/{name_ru}", response_model=JurisdictionCard)
def get_jurisdiction(name_ru: str, repo: FileDataRepository = Depends(get_repository)):
    """Return detailed card for a single jurisdiction by Russian name."""
    card = repo.get_jurisdiction(name_ru)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Jurisdiction not found: {name_ru}")
    return card
