"""
Level 3 v2 pipeline orchestrator (venue × instrument_class architecture).

Steps:
  prompts     — Build prompts algorithmically, save to prompts/level_3_v2/
  launch      — Submit Parallel tasks (venue × instrument_class × 3A/3B/3C)
  poll        — Poll until all tasks complete, save _parallel_raw/ files
  postprocess — LLM disaggregation: map tiers[] → per-cell files + translation
  validate    — LLM validation: scope/completeness/sources per cell
  all         — Run all steps sequentially (default)

Usage:
    python -m level_3.run_level3 [--step STEP]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.config import LEVEL3_V2_LOG_FILE, LOGS_DIR
from pipeline.logging_setup import get_logger
from level_3.venue_runner import (
    load_state,
    save_state,
    build_and_save_all_prompts,
    launch_all_venues,
    poll_all_venues,
)

LOGS_DIR.mkdir(parents=True, exist_ok=True)
logger = get_logger("run_level3_v2", LEVEL3_V2_LOG_FILE)

STEPS = ["prompts", "launch", "poll", "postprocess", "validate", "all"]


def run_postprocess(state: dict) -> None:
    """Import and run LLM disaggregation (postprocess_l3 module)."""
    try:
        from level_3.postprocess_l3 import postprocess_all_venues
        postprocess_all_venues(state)
    except ImportError:
        logger.warning("postprocess_l3 module not yet implemented — skipping postprocess step")


def run_validate(state: dict) -> None:
    """Import and run LLM validation (validator module)."""
    try:
        from level_3.validator import validate_all_venues
        validate_all_venues(state)
    except ImportError:
        logger.warning("validator module not yet implemented — skipping validate step")


def run_all() -> None:
    logger.info("========== Level 3 v2 Pipeline Start ==========")
    state = load_state()

    logger.info("--- Step 1: Build prompts ---")
    build_and_save_all_prompts(state)

    logger.info("--- Step 2: Launch Parallel tasks ---")
    launch_all_venues(state)

    logger.info("--- Step 3: Poll all tasks ---")
    poll_all_venues(state)

    logger.info("--- Step 4: Postprocess (disaggregate tiers → cells) ---")
    run_postprocess(state)

    logger.info("--- Step 5: Validate cell results ---")
    run_validate(state)

    logger.info("========== Level 3 v2 Pipeline Complete ==========")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Level 3 v2 — venue-level data collection")
    parser.add_argument("--step", choices=STEPS, default="all")
    args = parser.parse_args()

    if args.step == "all":
        run_all()
        sys.exit(0)

    state = load_state()

    if args.step == "prompts":
        build_and_save_all_prompts(state)
    elif args.step == "launch":
        launch_all_venues(state)
    elif args.step == "poll":
        poll_all_venues(state)
    elif args.step == "postprocess":
        run_postprocess(state)
    elif args.step == "validate":
        run_validate(state)
