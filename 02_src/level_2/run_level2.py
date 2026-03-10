"""
Level 2 full pipeline orchestrator.

Execution order:
  1. generate-prompts: LLM generates custom 2A prompts for each pilot venue
  2. launch-2a:        Submit 2A tasks to Parallel SDK (output_schema="auto")
  3. poll-2a:          Poll until all 2A tasks complete, save 2A_structure.json
  4. postprocess:      LLM postprocessing → venue_card.json + cells_list.json
                       + Level 3 prompts for every cell

Usage:
    python -m level_2.run_level2 [--step STEP]

    Where STEP is one of:
      generate-prompts   - Step 1: generate 2A prompts via LLM
      launch-2a          - Step 2: launch Parallel 2A tasks
      poll-2a            - Step 3: poll until all 2A tasks complete
      postprocess        - Step 4: LLM postprocessing (venue_card + cells + L3 prompts)
      all (default)      - Run all steps sequentially
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.config import LEVEL2_LOG_FILE
from pipeline.logging_setup import get_logger
from level_2.venue_runner import load_state, launch_all_2a, poll_all_2a
from level_2.prompt_generator import generate_all_prompts
from level_2.postprocess import process_all

logger = get_logger("run_level2", LEVEL2_LOG_FILE)


STEPS = [
    "generate-prompts",
    "launch-2a",
    "poll-2a",
    "postprocess",
    "all",
]


def run_all() -> None:
    logger.info("========== Level 2 Pipeline Start ==========")

    logger.info("--- Step 1: Generate 2A prompts via LLM ---")
    generate_all_prompts()

    state = load_state()

    logger.info("--- Step 2: Launch Parallel 2A tasks ---")
    launch_all_2a(state)

    logger.info("--- Step 3: Poll 2A tasks until complete ---")
    poll_all_2a(state)

    logger.info("--- Step 4: LLM postprocessing (venue_card + cells_list + L3 prompts) ---")
    process_all()

    logger.info("========== Level 2 Pipeline Complete ==========")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Level 2 full pipeline")
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

    if args.step == "generate-prompts":
        generate_all_prompts()
    elif args.step == "launch-2a":
        launch_all_2a(state)
    elif args.step == "poll-2a":
        poll_all_2a(state)
    elif args.step == "postprocess":
        process_all()
