"""
Level 4: Regulatory objectives and justifications.

Steps:
  parallel    — Launch Parallel API deep research, poll, save 4A_raw.json
  postprocess — LLM structured extraction + translation → level4.json
  validate    — Content validation → level4_validation.json
  all         — Run all three steps

Usage:
    python -m level_4.run_level4 [--step STEP]
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.config import (
    LEVEL4_LOG_FILE,
    LOGS_DIR,
    LLM_SMART_MODEL,
)
from pipeline.logging_setup import get_logger
from level_4.level4_runner import (
    run_level4_parallel,
    run_level4_postprocess,
    run_level4_validate,
    run_level4_all,
    _get_llm,
)

LOGS_DIR.mkdir(parents=True, exist_ok=True)
logger = get_logger("run_level4", LEVEL4_LOG_FILE)

STEPS = ["parallel", "postprocess", "validate", "all"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Level 4 — regulatory objectives research")
    parser.add_argument(
        "--step",
        choices=STEPS,
        default="all",
        help=(
            "Which step to run. "
            "'all' runs parallel -> postprocess -> validate."
        ),
    )
    args = parser.parse_args()

    if args.step == "all":
        llm = _get_llm(LLM_SMART_MODEL)
        run_level4_all(llm=llm)
        sys.exit(0)

    if args.step == "parallel":
        run_level4_parallel()
        sys.exit(0)

    if args.step == "postprocess":
        llm = _get_llm(LLM_SMART_MODEL)
        run_level4_postprocess(llm=llm)
        sys.exit(0)

    if args.step == "validate":
        run_level4_validate()
        sys.exit(0)
