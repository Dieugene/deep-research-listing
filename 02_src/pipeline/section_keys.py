"""
Task 011: L3 Parameters — section_keys[]

Deterministically maps lifecycle_phase_key → section_keys based on 3A/3B content.
Adds section_keys field to all parameters in pass2_ru.json and pass2.json files.
"""
import json
import datetime
from pathlib import Path
from typing import Any

from pipeline.config import COUNTRIES_DIR, LOGS_DIR
from pipeline.logging_setup import get_logger

logger = get_logger(
    "section_keys",
    LOGS_DIR / f"section_keys_{datetime.date.today()}.log"
)

# Empty values definition
EMPTY_VALUES = {"", "not applicable", "n/a", "not relevant", "н/д", "none"}


def _is_empty(description: str) -> bool:
    """Check if a description is empty or a placeholder."""
    if not isinstance(description, str):
        return True
    return description.strip().lower() in EMPTY_VALUES


def _load_json(path: Path) -> dict | None:
    """Load JSON file, return None if not found or invalid."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_json(path: Path, data: dict) -> None:
    """Save JSON file with ensure_ascii=False and indent=2."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_section_keys_for_phase(
    phase_key: str,
    raw_3a: dict | None,
    raw_3b: dict | None
) -> list[str]:
    """
    Determine section_keys based on lifecycle_phase_key and available content.

    Args:
        phase_key: lifecycle_phase_key value (e.g., "admission", "continuing")
        raw_3a: parsed 3A_raw.json (or None)
        raw_3b: parsed 3B_raw.json (or None)

    Returns:
        list[str]: section keys that apply to this phase
    """
    # Extract content dictionaries
    content_3a = raw_3a.get("content", {}) if raw_3a else {}
    content_3b = raw_3b.get("content", {}) if raw_3b else {}

    result = []

    # === ADMISSION ===
    if phase_key == "admission":
        # Sections from 3A that have non-empty description
        admission_sections = [
            "admission_overview",
            "eligibility_requirements",
            "instrument_requirements",
            "sponsor_and_infrastructure",
            "restrictions_and_lock_ups",
            "special_regimes",
            "procedure_and_timeline",
            "disclosure_at_admission",
            "secondary_admission",
        ]
        for section in admission_sections:
            if section in content_3a:
                desc = content_3a[section].get("description", "")
                if desc and not _is_empty(desc):
                    result.append(section)

    # === CONTINUING ===
    elif phase_key == "continuing":
        # Sub-keys from 3B content.continuing_obligations.*
        continuing_obs = content_3b.get("continuing_obligations", {})
        sub_keys = [
            "quantitative_thresholds",
            "qualitative_obligations",
            "compliance_confirmation",
            "periodic_reporting",
        ]
        for sub_key in sub_keys:
            if sub_key in continuing_obs:
                desc = continuing_obs[sub_key].get("description", "")
                if desc and not _is_empty(desc):
                    result.append(f"continuing_obligations.{sub_key}")

    # === SUSPENSION ===
    elif phase_key == "suspension":
        # Sub-keys from 3B content.suspension.*
        suspension = content_3b.get("suspension", {})
        sub_keys = ["grounds", "duration_limits", "procedure", "disclosure"]
        for sub_key in sub_keys:
            if sub_key in suspension:
                desc = suspension[sub_key].get("description", "")
                if desc and not _is_empty(desc):
                    result.append(f"suspension.{sub_key}")

    # === DELISTING / ENFORCEMENT ===
    elif phase_key in ("delisting", "enforcement") or \
         (isinstance(phase_key, str) and ("delist" in phase_key.lower() or "remov" in phase_key.lower())):
        result.extend(_delisting_keys(content_3b))

    # === MULTIPLE — parameter spans several lifecycle phases ===
    elif phase_key == "multiple":
        # Collect section_keys from ALL phases: admission + continuing + suspension + delisting
        # Admission sections from 3A
        admission_sections = [
            "admission_overview", "eligibility_requirements", "instrument_requirements",
            "sponsor_and_infrastructure", "restrictions_and_lock_ups", "special_regimes",
            "procedure_and_timeline", "disclosure_at_admission", "secondary_admission",
        ]
        for section in admission_sections:
            if section in content_3a:
                desc = content_3a[section].get("description", "")
                if desc and not _is_empty(desc):
                    result.append(section)

        # Continuing obligations from 3B
        continuing_obs = content_3b.get("continuing_obligations", {})
        for sub_key in ("quantitative_thresholds", "qualitative_obligations",
                        "compliance_confirmation", "periodic_reporting"):
            if sub_key in continuing_obs:
                desc = continuing_obs[sub_key].get("description", "")
                if desc and not _is_empty(desc):
                    result.append(f"continuing_obligations.{sub_key}")

        # Suspension from 3B
        suspension = content_3b.get("suspension", {})
        for sub_key in ("grounds", "duration_limits", "procedure", "disclosure"):
            if sub_key in suspension:
                desc = suspension[sub_key].get("description", "")
                if desc and not _is_empty(desc):
                    result.append(f"suspension.{sub_key}")

        # Delisting from 3B
        result.extend(_delisting_keys(content_3b))

    return result


def _delisting_keys(content_3b: dict) -> list[str]:
    """Extract non-empty delisting section keys from 3B content."""
    result = []
    delisting_comp = content_3b.get("delisting_compulsory", {})
    delisting_vol = content_3b.get("delisting_voluntary", {})

    for sub_key in ("grounds", "procedure", "grace_period", "shareholder_protection", "disclosure"):
        sub = delisting_comp.get(sub_key, {})
        desc = sub.get("description", "") if isinstance(sub, dict) else ""
        if desc and not _is_empty(desc):
            result.append(f"delisting_compulsory.{sub_key}")

    for sub_key in ("conditions", "procedure", "shareholder_approval"):
        sub = delisting_vol.get(sub_key, {})
        desc = sub.get("description", "") if isinstance(sub, dict) else ""
        if desc and not _is_empty(desc):
            result.append(f"delisting_voluntary.{sub_key}")

    return result


def _process_pass2_file(pass2_path: Path, cell_dir: Path) -> int:
    """
    Add section_keys to all parameters in one pass2 file.

    Args:
        pass2_path: Path to pass2_ru.json or pass2.json
        cell_dir: Directory containing 3A_raw.json and 3B_raw.json

    Returns:
        int: Number of parameters updated
    """
    # Load pass2 file
    data = _load_json(pass2_path)
    if not data:
        return 0

    # Load 3A and 3B raw data
    raw_3a = _load_json(cell_dir / "3A_raw.json")
    raw_3b = _load_json(cell_dir / "3B_raw.json")

    # Get list of parameters (could be "parameter_values" or "parameters")
    params = data.get("parameter_values", data.get("parameters", []))

    # Find found/extracted parameters
    found_params = [p for p in params if p.get("status") in ("found", "Найдено", "extracted")]

    # Check idempotency: skip if all found_params already have non-empty section_keys
    if all(p.get("section_keys") for p in found_params):
        return 0

    # Process each parameter
    updated_count = 0
    for param in params:
        # Update parameters with "found" status that have no or empty section_keys
        if param.get("status") in ("found", "Найдено", "extracted") and not param.get("section_keys"):
            phase_key = param.get("lifecycle_phase") or param.get("lifecycle_phase_key", "")
            section_keys = _get_section_keys_for_phase(phase_key, raw_3a, raw_3b)
            param["section_keys"] = section_keys
            updated_count += 1

    # Save updated file if changes were made
    if updated_count > 0:
        _save_json(pass2_path, data)

    return updated_count


def _process_cell(cell_dir: Path) -> bool:
    """
    Process one cell (add section_keys to parameters).

    Returns:
        bool: True if updated, False if skipped
    """
    cell_id = cell_dir.name

    # Check for pass2_ru.json first (priority)
    pass2_ru_path = cell_dir / "pass2_ru.json"
    pass2_path = cell_dir / "pass2.json"

    # Determine which files to process
    files_to_process = []

    if pass2_ru_path.exists():
        files_to_process.append(pass2_ru_path)
        # Also update pass2.json if it exists
        if pass2_path.exists():
            files_to_process.append(pass2_path)
    elif pass2_path.exists():
        files_to_process.append(pass2_path)
    else:
        return False

    # Process files
    total_updated = 0
    for file_path in files_to_process:
        updated = _process_pass2_file(file_path, cell_dir)
        total_updated += updated

    if total_updated == 0:
        logger.info("[SKIP] %s — all params already have section_keys", cell_id)
        return False
    else:
        logger.info("[UPDATED] %s — %d params updated", cell_id, total_updated)
        return True


def process_section_keys(jurisdictions: list[str] | None = None) -> None:
    """
    Iterate all cells, add section_keys to parameters.
    Idempotent: skips cells where all found parameters already have section_keys.

    Args:
        jurisdictions: Optional list of jurisdiction names to filter. If None, process all.
    """
    logger.info("Starting section_keys processing...")

    # Build set of jurisdiction names to filter
    jurisdiction_filter = None
    if jurisdictions:
        jurisdiction_filter = set(jurisdictions)

    total_updated = 0
    total_skipped = 0

    # Iterate all countries
    for country_dir in COUNTRIES_DIR.iterdir():
        if not country_dir.is_dir():
            continue

        # Filter by jurisdiction if specified
        if jurisdiction_filter and country_dir.name not in jurisdiction_filter:
            continue

        l3_dir = country_dir / "level_3"
        if not l3_dir.exists():
            continue

        # Iterate all venues in this country
        for venue_dir in l3_dir.iterdir():
            if not venue_dir.is_dir():
                continue

            # Iterate all cells in this venue
            for cell_dir in venue_dir.iterdir():
                if not cell_dir.is_dir():
                    continue

                if _process_cell(cell_dir):
                    total_updated += 1
                else:
                    total_skipped += 1

    logger.info("Completed section_keys processing: %d updated, %d skipped", total_updated, total_skipped)
