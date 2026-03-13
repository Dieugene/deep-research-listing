"""
FastAPI dependency injection for the DataRepository.
Singleton pattern. Chooses implementation based on DB_PATH env var.
"""
from __future__ import annotations
from core.config import DB_PATH
from repositories.file_repo import FileDataRepository

_repo = None


def get_repository():
    global _repo
    if _repo is None:
        if DB_PATH:
            import os
            if os.path.exists(DB_PATH):
                from repositories.sqlite_repo import SQLiteDataRepository
                _repo = SQLiteDataRepository(DB_PATH)
            else:
                import logging
                logging.getLogger(__name__).warning(
                    "DB_PATH is set to %s but file does not exist; falling back to FileDataRepository",
                    DB_PATH,
                )
                _repo = FileDataRepository()
        else:
            _repo = FileDataRepository()
    return _repo
