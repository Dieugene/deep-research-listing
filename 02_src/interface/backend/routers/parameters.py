"""
Parameter-level API endpoints: global summary and cross-jurisdiction comparison.
"""
from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_repository
from models.parameter import ParameterComparison, ParameterSummary
from repositories.file_repo import FileDataRepository

router = APIRouter(prefix="/parameters", tags=["parameters"])


@router.get("/", response_model=list[ParameterSummary])
def list_parameters(repo: FileDataRepository = Depends(get_repository)):
    """
    Return a summary of all parameters found across all cells and jurisdictions,
    sorted by parameter_id. Counts only entries with status='found'.
    """
    return repo.get_all_parameters()


@router.get("/{parameter_id}", response_model=ParameterComparison)
def get_parameter_comparison(
    parameter_id: str,
    repo: FileDataRepository = Depends(get_repository),
):
    """
    Return a cross-jurisdiction comparison for a specific parameter.
    Includes all cells where this parameter was found (status='found').
    Returns 404 if no data exists for this parameter_id.
    """
    comparison = repo.get_parameter_comparison(parameter_id)
    if comparison is None:
        raise HTTPException(
            status_code=404,
            detail=f"Parameter not found or no 'found' entries: {parameter_id}",
        )
    return comparison
