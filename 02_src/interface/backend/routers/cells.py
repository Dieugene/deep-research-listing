"""
Cell-level API endpoints: matrix view, content view, and parameters.
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from dependencies import get_repository
from models.cell import CellContent, MatrixView
from models.parameter import CellParameters
from repositories.file_repo import FileDataRepository

router = APIRouter(prefix="/cells", tags=["cells"])


@router.get("/{cell_id}/matrix", response_model=MatrixView)
def get_cell_matrix(
    cell_id: str,
    name_ru: str = Query(..., description="Russian name of the jurisdiction"),
    venue_key: str = Query(..., description="Venue key, e.g. LSE_Main_Market"),
    repo: FileDataRepository = Depends(get_repository),
):
    """
    Return the 4×5 data coverage matrix for a cell.
    Rows = lifecycle phases (admission, continuing, suspension, delisting).
    Columns = content types (requirements, procedures, monitoring, sanctions, disclosure).
    """
    matrix = repo.get_cell_matrix(name_ru, venue_key, cell_id)
    if matrix is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cell not found or has no data: {cell_id}",
        )
    return matrix


@router.get("/{cell_id}/content", response_model=CellContent)
def get_cell_content(
    cell_id: str,
    name_ru: str = Query(..., description="Russian name of the jurisdiction"),
    venue_key: str = Query(..., description="Venue key, e.g. LSE_Main_Market"),
    repo: FileDataRepository = Depends(get_repository),
):
    """
    Return the full textual content of a cell, organized by lifecycle phase
    (admission / maintenance / enforcement) and content sections.
    """
    content = repo.get_cell_content(name_ru, venue_key, cell_id)
    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cell not found or has no data: {cell_id}",
        )
    return content


@router.get("/{cell_id}/parameters", response_model=CellParameters)
def get_cell_parameters(
    cell_id: str,
    name_ru: str = Query(..., description="Russian name of the jurisdiction"),
    venue_key: str = Query(..., description="Venue key, e.g. LSE_Main_Market"),
    repo: FileDataRepository = Depends(get_repository),
):
    """
    Return the structured parameter values (pass2) for a cell.
    """
    params = repo.get_cell_parameters(name_ru, venue_key, cell_id)
    if params is None:
        raise HTTPException(
            status_code=404,
            detail=f"Parameters not found for cell: {cell_id}",
        )
    return params
