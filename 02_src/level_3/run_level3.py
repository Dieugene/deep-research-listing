"""
Level 3 full pipeline orchestrator: collect raw research data for each cell.

Execution order:
  1. launch: Submit 3A/3B/3C/3D tasks to Parallel SDK for every cell
  2. poll:   Poll until all tasks complete, save raw JSON results
  3. all:    Run launch then poll sequentially

Usage:
    python -m level_3.run_level3 [--step STEP]

    Where STEP is one of:
      launch     - Step 1: launch Parallel tasks for all cells
      poll       - Step 2: poll until all tasks complete
      all        - Run both steps sequentially (default)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.config import LEVEL3_LOG_FILE, LOGS_DIR
from pipeline.logging_setup import get_logger
from level_3.cell_runner import load_state, launch_all_cells, poll_all_cells

LOGS_DIR.mkdir(parents=True, exist_ok=True)

logger = get_logger("run_level3", LEVEL3_LOG_FILE)

STEPS = ["launch", "poll", "all"]


def run_all() -> None:
    logger.info("========== Level 3 Pipeline Start ==========")

    state = load_state()

    logger.info("--- Step 1: Launch Parallel tasks for all cells ---")
    launch_all_cells(state)

    logger.info("--- Step 2: Poll all tasks until complete ---")
    poll_all_cells(state)

    logger.info("========== Level 3 Pipeline Complete ==========")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Level 3 full pipeline — cell data collection")
    parser.add_argument(
        "--step",
        choices=STEPS,
        default="all",
        help="Which step to run (default: all)",
    )
    args = parser.parse_args()

    if args.step == "all":
        run_all()
        sys.exit(0)

    state = load_state()

    if args.step == "launch":
        logger.info("--- Launch: submitting Parallel tasks for all cells ---")
        launch_all_cells(state)
    elif args.step == "poll":
        logger.info("--- Poll: waiting for all Level 3 tasks to complete ---")
        poll_all_cells(state)
