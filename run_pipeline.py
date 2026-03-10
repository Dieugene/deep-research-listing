"""
Convenience entry point for running the Level 1 pipeline from project root.

Usage:
    python run_pipeline.py [--step STEP]

Steps: eu | launch-1a | poll-1a | import-institutional | launch-1c | poll-1c | postprocess | all (default)

Requires:
    - .env with OPENAI_API_KEY, OPENAI_BASE_URL, PARALLEL_API_KEY
    - venv activated with: pip install parallel-web langchain-openai python-dotenv pydantic
"""
import sys
from pathlib import Path

# Add 02_src to Python path
SRC_DIR = Path(__file__).resolve().parent / "02_src"
sys.path.insert(0, str(SRC_DIR))

# Run the level 1 orchestrator
from level_1.run_level1 import run_all
import argparse

STEPS = ["eu", "launch-1a", "poll-1a", "import-institutional", "launch-1c", "poll-1c", "postprocess", "all"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Level 1 pipeline runner")
    parser.add_argument("--step", choices=STEPS, default="all", help="Step to run")
    args = parser.parse_args()

    from pipeline.parallel_runner import load_state
    from level_1.eu_framework import run_full as run_eu
    from level_1.jurisdiction_runner import launch_all_1a, poll_all_1a, launch_all_1c, poll_all_1c
    from level_1.import_institutional import import_all
    from level_1.postprocess import process_all
    from pipeline.logging_setup import get_logger

    logger = get_logger("run_pipeline")
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
        import_all()
    elif args.step == "launch-1c":
        launch_all_1c(state)
    elif args.step == "poll-1c":
        poll_all_1c(state)
    elif args.step == "postprocess":
        process_all()
