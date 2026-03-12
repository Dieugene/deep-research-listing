"""
Level 2: Launch and poll Parallel 2A Deep Research tasks for pilot venues.

Each venue gets one 2A task with output_schema="auto" (Parallel determines structure).
State is persisted in 04_logs/level2_state.json for resumable execution.

Usage:
    python -m level_2.venue_runner --launch
    python -m level_2.venue_runner --poll
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.config import (
    PILOT_VENUES,
    LEVEL2_STATE_FILE,
    PROMPTS_LEVEL2_DIR,
    get_country_level2_dir,
)
from pipeline.storage import load_json, save_json, now_iso
from pipeline.parallel_runner import launch_task, poll_all, save_state as _runner_save_state
from pipeline.logging_setup import get_logger
from pipeline.config import LEVEL2_LOG_FILE

logger = get_logger("venue_runner", LEVEL2_LOG_FILE)


# ---------------------------------------------------------------------------
# State management (level2-specific state file)
# ---------------------------------------------------------------------------

def load_state() -> dict:
    """Load level2 state from disk (or return empty state)."""
    data = load_json(LEVEL2_STATE_FILE)
    if data is None:
        return {"tasks": {}}
    return data


def save_state(state: dict) -> None:
    """Persist level2 state to disk."""
    _runner_save_state(state, LEVEL2_STATE_FILE)


def _task_key(venue_key: str) -> str:
    return f"{venue_key}_2A"


# ---------------------------------------------------------------------------
# Save function factory
# ---------------------------------------------------------------------------

def _make_save_fn(venue: dict):
    """Return a save function for poll_all that writes 2A_structure.json."""
    name_ru = venue["name_ru"]
    venue_key = venue["venue_key"]
    venue_name_english = venue["venue_name_english"]

    def save_fn(content) -> Path:
        d = get_country_level2_dir(name_ru, venue_key)
        path = d / "2A_structure.json"
        if isinstance(content, dict):
            data = {
                "venue_key": venue_key,
                "venue_name_english": venue_name_english,
                "retrieved_at": now_iso(),
                **content,
            }
        else:
            # Plain text / unexpected format — wrap it
            data = {
                "venue_key": venue_key,
                "venue_name_english": venue_name_english,
                "retrieved_at": now_iso(),
                "content": str(content),
            }
        save_json(path, data)
        return path

    return save_fn


# ---------------------------------------------------------------------------
# Launch / poll helpers
# ---------------------------------------------------------------------------

def launch_all_2a(state: dict, venues: list = None) -> None:
    """Launch 2A Parallel tasks for all PILOT_VENUES."""
    for venue in (venues or PILOT_VENUES):
        venue_key = venue["venue_key"]
        task_key = _task_key(venue_key)

        # Load the pre-generated prompt
        prompt_path = PROMPTS_LEVEL2_DIR / f"{venue_key}_prompt.txt"
        if not prompt_path.exists():
            logger.error(
                "Prompt for %s not found at %s — run generate-prompts step first.",
                venue_key,
                prompt_path,
            )
            continue

        with open(prompt_path, encoding="utf-8") as f:
            prompt = f.read()

        launch_task(
            task_key=task_key,
            prompt=prompt,
            output_schema="auto",
            processor="core",
            state=state,
            state_file=LEVEL2_STATE_FILE,
        )

    save_state(state)
    logger.info("All 2A tasks launched.")


def poll_all_2a(state: dict, venues: list = None) -> dict:
    """Poll all 2A tasks until complete. Returns {task_key: content_or_None}."""
    tasks = []
    for venue in (venues or PILOT_VENUES):
        venue_key = venue["venue_key"]
        task_key = _task_key(venue_key)
        if task_key in state["tasks"]:
            tasks.append((task_key, _make_save_fn(venue)))
        else:
            logger.warning("Task %s not found in state — was it launched?", task_key)

    return poll_all(tasks, state, state_file=LEVEL2_STATE_FILE)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Level 2 venue runner")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--launch", action="store_true", help="Launch 2A tasks")
    group.add_argument("--poll", action="store_true", help="Poll until all done")
    args = parser.parse_args()

    state = load_state()

    if args.launch:
        launch_all_2a(state)
    elif args.poll:
        poll_all_2a(state)
