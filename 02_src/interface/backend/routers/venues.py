"""
Venue-level API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_repository
from models.venue import VenueCard
from repositories.file_repo import FileDataRepository

router = APIRouter(prefix="/venues", tags=["venues"])


@router.get("/{venue_key}", response_model=VenueCard)
def get_venue(venue_key: str, repo: FileDataRepository = Depends(get_repository)):
    """Return the full venue card, including its list of cells."""
    card = repo.get_venue(venue_key)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Venue not found: {venue_key}")
    return card
