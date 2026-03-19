"""
Catch-up script: run Phase 2 (pass2.json + pass2_ru.json) for all jurisdictions
that are missing those files.

This script is intended as a one-time catch-up to bring AU/DE/SG/FR (and any
other jurisdiction without pass2.json) up to date.

All Phase 2 steps are idempotent — safe to run on jurisdictions that already
have partial or complete output; existing files will be skipped automatically.

Steps per jurisdiction cell (skipped if output already exists):
  1. form_groups      — build group_meta.json files (idempotent)
  2. run_pass1        — extract parameter structure per group → pass1.json (idempotent)
  3. run_new_pass2    — extract parameter values per cell → pass2.json (idempotent)
  4. run_pass2_translate — translate pass2.json → pass2_ru.json (idempotent)

Usage:
    cd 02_src
    venv\\Scripts\\python.exe tools/run_phase2_catchup.py [--dry-run]

Options:
    --dry-run   Only log which cells are missing pass2.json / pass2_ru.json,
                do not run any LLM calls.
"""

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — must come before project imports
# ---------------------------------------------------------------------------

_TOOLS_DIR = Path(__file__).resolve().parent   # 02_src/tools/
_SRC_DIR = _TOOLS_DIR.parent                   # 02_src/
_PROJECT_ROOT = _SRC_DIR.parent                # project root

sys.path.insert(0, str(_SRC_DIR))

from dotenv import load_dotenv
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

from pipeline.config import (
    COUNTRIES_DIR,
    PHASE2_LOG_FILE,
    LOGS_DIR,
    LLM_SMART_MODEL,
    LLM_FAST_MODEL,
)
from pipeline.logging_setup import get_logger
from level_3.phase2_runner import (
    load_state,
    form_groups,
    run_pass1,
    run_new_pass2,
    run_pass2_translate,
    _get_llm,
)

LOGS_DIR.mkdir(parents=True, exist_ok=True)
logger = get_logger("phase2_catchup", PHASE2_LOG_FILE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scan_cells() -> dict:
    """
    Scan COUNTRIES_DIR and return a status dict for every cell directory.

    Returns:
        {
            "<country>/<venue>/<cell_id>": {
                "country": str,
                "has_pass2": bool,
                "has_pass2_ru": bool,
            },
            ...
        }
    """
    status: dict = {}

    for country_dir in sorted(COUNTRIES_DIR.iterdir()):
        if not country_dir.is_dir():
            continue
        level3_base = country_dir / "level_3"
        if not level3_base.exists():
            continue

        for venue_dir in sorted(level3_base.iterdir()):
            if not venue_dir.is_dir() or venue_dir.name == "_groups":
                continue

            for cell_dir in sorted(venue_dir.iterdir()):
                if not cell_dir.is_dir():
                    continue

                key = f"{country_dir.name}/{venue_dir.name}/{cell_dir.name}"
                status[key] = {
                    "country": country_dir.name,
                    "has_pass2": (cell_dir / "pass2.json").exists(),
                    "has_pass2_ru": (cell_dir / "pass2_ru.json").exists(),
                }

    return status


def _log_status(status: dict) -> None:
    """Log a human-readable status table."""
    total = len(status)
    missing_pass2 = [k for k, v in status.items() if not v["has_pass2"]]
    missing_pass2_ru = [k for k, v in status.items() if not v["has_pass2_ru"]]
    complete = [k for k, v in status.items() if v["has_pass2"] and v["has_pass2_ru"]]

    logger.info("=" * 60)
    logger.info("PHASE 2 CATCH-UP STATUS SCAN")
    logger.info("=" * 60)
    logger.info("Total cell directories found: %d", total)
    logger.info("  Complete (pass2.json + pass2_ru.json): %d", len(complete))
    logger.info("  Missing pass2.json:                    %d", len(missing_pass2))
    logger.info("  Missing pass2_ru.json only:            %d",
                len([k for k in missing_pass2_ru if k not in missing_pass2]))
    logger.info("")

    if missing_pass2:
        logger.info("Cells missing pass2.json:")
        for k in missing_pass2:
            logger.info("  [NO pass2    ] %s", k)

    ru_only_missing = [k for k in missing_pass2_ru if k not in missing_pass2]
    if ru_only_missing:
        logger.info("Cells with pass2.json but missing pass2_ru.json:")
        for k in ru_only_missing:
            logger.info("  [NO pass2_ru ] %s", k)

    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Main catch-up runner
# ---------------------------------------------------------------------------

def run_catchup(dry_run: bool = False) -> None:
    """
    Scan all cells, log status, then run Phase 2 steps for cells that need it.

    Steps are idempotent — existing output files are always skipped.
    """
    logger.info("========== Phase 2 Catch-Up Start ==========")

    # 1. Scan and log
    status = _scan_cells()
    _log_status(status)

    if dry_run:
        logger.info("DRY RUN mode — no LLM calls will be made.")
        logger.info("========== Phase 2 Catch-Up (dry run) Complete ==========")
        return

    # 2. Check whether any work is needed
    needs_pass2 = any(not v["has_pass2"] for v in status.values())
    needs_translate = any(not v["has_pass2_ru"] for v in status.values())

    if not needs_pass2 and not needs_translate:
        logger.info("All cells are complete — nothing to do.")
        logger.info("========== Phase 2 Catch-Up Complete ==========")
        return

    # 3. Load state (shared across all Phase 2 steps)
    state = load_state()

    # 4. Steps 1-2: form_groups + pass1
    #    These are group-level — run unconditionally (both are idempotent).
    if needs_pass2:
        logger.info("--- Catch-Up Step 1: Form groups ---")
        form_groups(state)

        logger.info("--- Catch-Up Step 2: Pass 1 (parameter structure) ---")
        run_pass1(state)

        logger.info("--- Catch-Up Step 3: Pass 2 New (parameter values per cell) ---")
        llm_smart = _get_llm(LLM_SMART_MODEL)
        run_new_pass2(state=state, llm=llm_smart)
    else:
        logger.info("All cells already have pass2.json — skipping form_groups/pass1/pass2-new")

    # 5. Step 4: translate — always run (it is self-idempotent via per-cell skip)
    if needs_translate:
        logger.info("--- Catch-Up Step 4: Translate (pass2 → pass2_ru) ---")
        llm_translate = _get_llm(LLM_FAST_MODEL)
        run_pass2_translate(llm=llm_translate)
    else:
        logger.info("All cells already have pass2_ru.json — skipping translate")

    logger.info("========== Phase 2 Catch-Up Complete ==========")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 2 catch-up: generate pass2.json + pass2_ru.json for all cells"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Only scan and log status — do not run any LLM calls",
    )
    args = parser.parse_args()

    run_catchup(dry_run=args.dry_run)
