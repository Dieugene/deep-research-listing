"""
Shared Pydantic types used across multiple models.
"""
from enum import Enum


class ValidationStatus(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    UNKNOWN = "unknown"


class MatrixCellStatus(str, Enum):
    FILLED = "filled"
    NOT_FILLED = "not_filled"
    NOT_APPLICABLE = "not_applicable"
