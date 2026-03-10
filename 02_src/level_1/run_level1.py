"""
Level 1 full pipeline orchestrator.

Executes in the correct order:
  1. EU Framework
  2. 1A for UK, HK, Russia (parallel launch, then poll)
  3. Import institutional factors (1B) from pre-collected MD file
  4. 1C for all jurisdictions (parallel launch, then poll; uses 1A context)
  5. LLM postprocessing for all jurisdictions

This script is the single entry point for a full Level 1 run.

Usage:
    python -m level_1.run_level1 [--step STEP]

    Where STEP is one of:
      eu                   - Run EU framework only
      launch-1a            - Launch 1A tasks only
      poll-1a              - Poll 1A tasks until done
      import-institutional - Import 1B from MD file (replaces Parallel 1B)
      launch-1c            - Launch 1C tasks
      poll-1c              - Poll 1C tasks
      postprocess          - Run LLM postprocessing
      all (default)        - Run all steps sequentially
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.logging_setup import get_logger
from pipeline.parallel_runner import load_state

from level_1.eu_framework import run_full as run_eu
from level_1.jurisdiction_runner import (
    launch_all_1a, poll_all_1a,
    launch_all_1c, poll_all_1c,
)
from level_1.import_institutional import import_all as import_institutional
from level_1.postprocess import process_all

logger = get_logger("run_level1")


STEPS = [
    "eu",
    "launch-1a",
    "poll-1a",
    "import-institutional",
    "launch-1c",
    "poll-1c",
    "postprocess",
    "all",
]


def run_all():
    logger.info("========== Level 1 Pipeline Start ==========")

    logger.info("--- Step 1: EU Framework ---")
    run_eu()

    state = load_state()

    logger.info("--- Step 2: Launch 1A for all jurisdictions ---")
    launch_all_1a(state)

    logger.info("--- Step 3: Poll 1A until complete ---")
    poll_all_1a(state)

    logger.info("--- Step 4: Import institutional factors (1B) from MD ---")
    import_institutional()

    logger.info("--- Step 5: Launch 1C for all jurisdictions ---")
    launch_all_1c(state)

    logger.info("--- Step 6: Poll 1C until complete ---")
    poll_all_1c(state)

    logger.info("--- Step 7: LLM postprocessing ---")
    process_all()

    logger.info("========== Level 1 Pipeline Complete ==========")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Level 1 full pipeline")
    parser.add_argument(
        "--step",
        choices=STEPS,
        default="all",
        help="Which step to run (default: all)",
    )
    args = parser.parse_args()

    state = load_state()

    if args.step == "all":
        run_all()
    elif args.step == "eu":
        run_eu()
    elif args.step == "launch-1a":
        launch_all_1a(state)
    elif args.step == "poll-1a":
        poll_all_1a(state)
    elif args.step == "import-institutional":
        import_institutional()
    elif args.step == "launch-1c":
        launch_all_1c(state)
    elif args.step == "poll-1c":
        poll_all_1c(state)
    elif args.step == "postprocess":
        process_all()
