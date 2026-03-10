"""
Data loading utilities for the Streamlit viewer.
Reads pipeline output files (L1, L2, L3) without any LLM calls.
"""
from pipeline.config import (
    COUNTRIES_DIR,
    LEVEL3_STATE_FILE,
    get_country_level2_dir,
    get_country_level3_dir,
)
from pipeline.storage import load_json


def load_jurisdiction_card(name_ru: str) -> dict | None:
    path = COUNTRIES_DIR / name_ru / "level_1" / "jurisdiction_card.json"
    return load_json(path)


def load_venue_card(name_ru: str, venue_key: str) -> dict | None:
    return load_json(get_country_level2_dir(name_ru, venue_key) / "venue_card.json")


def load_cells_list(name_ru: str, venue_key: str) -> list | None:
    """
    Load cells list. Handles both plain list and {"cells": [...]} envelope formats.
    Returns a list of cell dicts, or None if file not found.
    """
    data = load_json(get_country_level2_dir(name_ru, venue_key) / "cells_list.json")
    if data is None:
        return None
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "cells" in data:
        return data["cells"]
    return []


def load_level3_state() -> dict:
    data = load_json(LEVEL3_STATE_FILE)
    return data if data else {"tasks": {}}


def get_l3_status(
    name_ru: str,
    venue_key: str,
    cell_id: str,
    query_type: str,
    cell_index: int = 0,
    state: dict | None = None,
) -> str:
    """
    Return 'done' | 'pending' | 'not started' for a given cell+query_type.

    Priority:
    1. File exists on disk -> 'done'
    2. Entry in level3_state.json with a non-done status -> 'pending'
    3. Otherwise -> 'not started'
    """
    base = get_country_level3_dir(name_ru, venue_key)

    # Check both folder naming conventions: plain cell_id and cell_id_{index}
    for folder in [f"{cell_id}", f"{cell_id}_{cell_index}"]:
        path = base / folder / f"{query_type}_raw.json"
        if path.exists():
            return "done"

    # Fall back to state file
    if state is None:
        state = load_level3_state()

    for key in [
        f"{cell_id}_{query_type}",
        f"{cell_id}_{query_type}_{cell_index}",
    ]:
        task = state["tasks"].get(key, {})
        status = task.get("status")
        # Intentional: state "done" without file on disk = treat as "not started" (filesystem is ground truth)
        if status and status != "done":
            return "pending"

    return "not started"


def load_l3_result(
    name_ru: str,
    venue_key: str,
    cell_id: str,
    query_type: str,
    cell_index: int = 0,
) -> dict | None:
    """
    Load raw L3 JSON for a cell+query_type.
    Tries both folder naming conventions; returns None if not found.
    """
    base = get_country_level3_dir(name_ru, venue_key)
    for folder in [f"{cell_id}", f"{cell_id}_{cell_index}"]:
        result = load_json(base / folder / f"{query_type}_raw.json")
        if result is not None:
            return result
    return None
