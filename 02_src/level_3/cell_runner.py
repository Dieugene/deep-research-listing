"""
Level 3: Launch and poll Parallel Deep Research tasks for each cell.

For each cell in cells_list.json, tasks 3A, 3B, 3C are always launched.
Task 3D is launched only when secondary_admission_applicable=True.

State is persisted in 04_logs/level3_state.json for resumable execution.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.config import (
    LEVEL3_STATE_FILE,
    LEVEL3_LOG_FILE,
    PILOT_VENUES,
    get_country_level3_dir,
    get_country_level2_dir,
)
from pipeline.storage import load_json, save_json, now_iso
from pipeline.parallel_runner import launch_task, poll_all, save_state as _runner_save_state
from pipeline.logging_setup import get_logger

logger = get_logger("cell_runner", LEVEL3_LOG_FILE)


# ---------------------------------------------------------------------------
# Output schemas — proper JSON Schema format required by Parallel API
# Root must have "type": "object", "properties", "required", "additionalProperties": false
# ---------------------------------------------------------------------------

def _obj() -> dict:
    """Helper: a nested object with description and source string fields."""
    return {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "source": {"type": "string"},
        },
    }


SCHEMA_3A = {
    "type": "object",
    "properties": {
        "admission_overview": _obj(),
        "eligibility_requirements": _obj(),
        "instrument_requirements": _obj(),
        "sponsor_and_infrastructure": _obj(),
        "restrictions_and_lock_ups": _obj(),
        "procedure_and_timeline": _obj(),
        "disclosure_at_admission": _obj(),
        "special_regimes": _obj(),
        "additional_findings": _obj(),
    },
    "required": [
        "admission_overview",
        "eligibility_requirements",
        "instrument_requirements",
        "sponsor_and_infrastructure",
        "restrictions_and_lock_ups",
        "procedure_and_timeline",
        "disclosure_at_admission",
        "special_regimes",
        "additional_findings",
    ],
    "additionalProperties": False,
}

SCHEMA_3B = {
    "type": "object",
    "properties": {
        "continuing_obligations": {
            "type": "object",
            "properties": {
                "quantitative_thresholds": _obj(),
                "qualitative_obligations": _obj(),
                "periodic_reporting": _obj(),
                "compliance_confirmation": _obj(),
            },
            "required": ["quantitative_thresholds", "qualitative_obligations",
                         "periodic_reporting", "compliance_confirmation"],
            "additionalProperties": False,
        },
        "suspension": {
            "type": "object",
            "properties": {
                "grounds": _obj(),
                "procedure": _obj(),
                "disclosure": _obj(),
                "duration_limits": _obj(),
            },
            "required": ["grounds", "procedure", "disclosure", "duration_limits"],
            "additionalProperties": False,
        },
        "delisting_compulsory": {
            "type": "object",
            "properties": {
                "grounds": _obj(),
                "procedure": _obj(),
                "grace_period": _obj(),
                "shareholder_protection": _obj(),
                "disclosure": _obj(),
            },
            "required": ["grounds", "procedure", "grace_period",
                         "shareholder_protection", "disclosure"],
            "additionalProperties": False,
        },
        "delisting_voluntary": {
            "type": "object",
            "properties": {
                "conditions": _obj(),
                "procedure": _obj(),
                "shareholder_approval": _obj(),
            },
            "required": ["conditions", "procedure", "shareholder_approval"],
            "additionalProperties": False,
        },
        "terminology": {
            "type": "object",
            "properties": {
                "delisting_local_term": {"type": "string"},
                "suspension_local_term": {"type": "string"},
                "source": {"type": "string"},
            },
            "required": ["delisting_local_term", "suspension_local_term", "source"],
            "additionalProperties": False,
        },
        "additional_findings": _obj(),
    },
    "required": [
        "continuing_obligations", "suspension", "delisting_compulsory",
        "delisting_voluntary", "terminology", "additional_findings",
    ],
    "additionalProperties": False,
}

SCHEMA_3C = {
    "type": "object",
    "properties": {
        "monitoring_regime": {
            "type": "object",
            "properties": {
                "responsible_body": _obj(),
                "mechanisms": _obj(),
                "sponsor_role": _obj(),
                "issuer_reporting_to_exchange": _obj(),
            },
            "required": ["responsible_body", "mechanisms", "sponsor_role",
                         "issuer_reporting_to_exchange"],
            "additionalProperties": False,
        },
        "sanctions": {
            "type": "object",
            "properties": {
                "exchange_sanctions": _obj(),
                "regulator_sanctions": _obj(),
                "disciplinary_procedure": _obj(),
                "publication_of_actions": _obj(),
            },
            "required": ["exchange_sanctions", "regulator_sanctions",
                         "disciplinary_procedure", "publication_of_actions"],
            "additionalProperties": False,
        },
        "enforcement_practice": {
            "type": "object",
            "properties": {
                "recent_examples": _obj(),
                "general_approach": _obj(),
            },
            "required": ["recent_examples", "general_approach"],
            "additionalProperties": False,
        },
        "additional_findings": _obj(),
    },
    "required": ["monitoring_regime", "sanctions", "enforcement_practice", "additional_findings"],
    "additionalProperties": False,
}

SCHEMA_3D = {
    "type": "object",
    "properties": {
        "eligibility": {
            "type": "object",
            "properties": {
                "qualifying_exchanges": _obj(),
                "market_cap_threshold": _obj(),
                "track_record": _obj(),
            },
            "required": ["qualifying_exchanges", "market_cap_threshold", "track_record"],
            "additionalProperties": False,
        },
        "waivers_from_standard": _obj(),
        "additional_requirements": _obj(),
        "continuing_obligations_differences": _obj(),
        "secondary_vs_dual_primary": _obj(),
        "additional_findings": _obj(),
    },
    "required": [
        "eligibility", "waivers_from_standard", "additional_requirements",
        "continuing_obligations_differences", "secondary_vs_dual_primary", "additional_findings",
    ],
    "additionalProperties": False,
}

SCHEMAS = {
    "3A": SCHEMA_3A,
    "3B": SCHEMA_3B,
    "3C": SCHEMA_3C,
    "3D": SCHEMA_3D,
}


# ---------------------------------------------------------------------------
# State management (level3-specific state file)
# ---------------------------------------------------------------------------

def load_state() -> dict:
    """Load level3 state from disk (or return empty state)."""
    data = load_json(LEVEL3_STATE_FILE)
    if data is None:
        return {"tasks": {}}
    return data


def save_state(state: dict) -> None:
    """Persist level3 state to disk."""
    _runner_save_state(state, LEVEL3_STATE_FILE)


# ---------------------------------------------------------------------------
# Task key and path helpers
# ---------------------------------------------------------------------------

def _make_task_key(cell_id: str, query_type: str, i: int, has_duplicate: bool) -> str:
    """
    Build a unique task key.

    For cells with duplicate cell_ids (AQSE Access/Apex, HKEX 主板/創業板),
    append the 0-based index to disambiguate.
    """
    if has_duplicate:
        return f"{cell_id}_{query_type}_{i}"
    return f"{cell_id}_{query_type}"


def _make_cell_dir(cell: dict, name_ru: str, i: int, has_duplicate: bool) -> Path:
    """
    Return the output directory for a cell's raw results.

    Duplicate cell_ids get a suffixed folder: {cell_id}_{i}/
    """
    cell_id = cell["cell_id"]
    venue_key = cell["venue_key"]
    base_dir = get_country_level3_dir(name_ru, venue_key)
    if has_duplicate:
        folder_name = f"{cell_id}_{i}"
    else:
        folder_name = cell_id
    return base_dir / folder_name


def _make_save_fn(cell: dict, query_type: str, name_ru: str, i: int, has_duplicate: bool):
    """Return a save function for poll_all that writes {type}_raw.json."""
    cell_id = cell["cell_id"]
    venue_key = cell["venue_key"]
    cell_dir = _make_cell_dir(cell, name_ru, i, has_duplicate)

    def save_fn(content) -> Path:
        path = cell_dir / f"{query_type}_raw.json"
        data = {
            "cell_id": cell_id,
            "venue_key": venue_key,
            "query_type": query_type,
            "retrieved_at": now_iso(),
            "content": content,
        }
        save_json(path, data)
        return path

    return save_fn


# ---------------------------------------------------------------------------
# Load cells from a venue's cells_list.json
# ---------------------------------------------------------------------------

def load_cells(cells_list_path: Path) -> list:
    """Read and return the cells list from a cells_list.json file."""
    data = load_json(cells_list_path)
    if data is None:
        logger.error("cells_list.json not found at %s", cells_list_path)
        return []
    return data.get("cells", [])


def _find_duplicate_cell_ids(cells: list) -> set:
    """Return a set of cell_ids that appear more than once in the list."""
    seen = {}
    for cell in cells:
        cid = cell["cell_id"]
        seen[cid] = seen.get(cid, 0) + 1
    return {cid for cid, count in seen.items() if count > 1}


# ---------------------------------------------------------------------------
# Build the full task list across all pilot venues
# ---------------------------------------------------------------------------

def _build_task_list() -> list[dict]:
    """
    Build a flat list of task descriptors across all pilot venues.

    Each entry: {
        task_key, cell, query_type, prompt_path,
        name_ru, i, has_duplicate
    }
    """
    tasks = []
    for venue in PILOT_VENUES:
        venue_key = venue["venue_key"]
        name_ru = venue["name_ru"]
        cells_list_path = get_country_level2_dir(name_ru, venue_key) / "cells_list.json"
        cells = load_cells(cells_list_path)
        if not cells:
            logger.warning("No cells found for venue %s", venue_key)
            continue

        duplicate_ids = _find_duplicate_cell_ids(cells)

        for i, cell in enumerate(cells):
            cell_id = cell["cell_id"]
            has_duplicate = cell_id in duplicate_ids
            prompts = cell.get("prompts", {})
            secondary_applicable = cell.get("secondary_admission_applicable", False)

            # Always: 3A, 3B, 3C
            query_types = ["3A", "3B", "3C"]
            # Conditionally: 3D
            if secondary_applicable and prompts.get("3D"):
                query_types.append("3D")

            for query_type in query_types:
                prompt_path_str = prompts.get(query_type)
                if not prompt_path_str:
                    logger.warning(
                        "No prompt path for cell %s query_type %s — skipping",
                        cell_id, query_type,
                    )
                    continue
                task_key = _make_task_key(cell_id, query_type, i, has_duplicate)
                tasks.append({
                    "task_key": task_key,
                    "cell": cell,
                    "query_type": query_type,
                    "prompt_path": Path(prompt_path_str),
                    "name_ru": name_ru,
                    "i": i,
                    "has_duplicate": has_duplicate,
                })

    return tasks


# ---------------------------------------------------------------------------
# Launch / poll
# ---------------------------------------------------------------------------

def launch_all_cells(state: dict) -> None:
    """Launch Parallel 3A/3B/3C/3D tasks for all cells in all pilot venues."""
    task_list = _build_task_list()
    logger.info("Total tasks to launch: %d", len(task_list))

    for item in task_list:
        task_key = item["task_key"]
        prompt_path = item["prompt_path"]
        query_type = item["query_type"]
        cell_id = item["cell"]["cell_id"]

        if not prompt_path.exists():
            logger.error(
                "Prompt file not found for cell %s query_type %s: %s",
                cell_id, query_type, prompt_path,
            )
            continue

        with open(prompt_path, encoding="utf-8") as f:
            prompt = f.read()

        launch_task(
            task_key=task_key,
            prompt=prompt,
            output_schema=SCHEMAS[query_type],
            processor="core",
            state=state,
            state_file=LEVEL3_STATE_FILE,
        )

    save_state(state)
    logger.info("All Level 3 tasks launched.")


def poll_all_cells(state: dict) -> dict:
    """Poll all Level 3 tasks until complete. Returns {task_key: content_or_None}."""
    task_list = _build_task_list()
    tasks_to_poll = []

    for item in task_list:
        task_key = item["task_key"]
        if task_key not in state["tasks"]:
            logger.warning("Task %s not found in state — was it launched?", task_key)
            continue
        save_fn = _make_save_fn(
            cell=item["cell"],
            query_type=item["query_type"],
            name_ru=item["name_ru"],
            i=item["i"],
            has_duplicate=item["has_duplicate"],
        )
        tasks_to_poll.append((task_key, save_fn))

    return poll_all(tasks_to_poll, state, state_file=LEVEL3_STATE_FILE)
