"""
FastAPI dependency injection for the DataRepository.
The repository is instantiated once and reused across all requests (singleton pattern).
"""
from repositories.file_repo import FileDataRepository

_repo: FileDataRepository | None = None


def get_repository() -> FileDataRepository:
    global _repo
    if _repo is None:
        _repo = FileDataRepository()
    return _repo
