"""
Level 1: Run queries 1A, 1C for pilot jurisdictions.

1B (institutional factors) is now imported from a pre-collected MD file
via import_institutional.py — not run as a Parallel query.

Execution flow:
  1. Launch 1A for all 3 jurisdictions in parallel (non-blocking launch)
  2. Poll all 1A tasks until done
  3. For each jurisdiction: launch 1C (with 1A context)
  4. Poll all 1C tasks until done

Usage:
    python -m level_1.jurisdiction_runner --launch-1a
    python -m level_1.jurisdiction_runner --poll-1a
    python -m level_1.jurisdiction_runner --launch-1c
    python -m level_1.jurisdiction_runner --poll-1c
    python -m level_1.jurisdiction_runner --run-all   # full run (default)
"""
# RULE: Never truncate data passed to LLM prompts.
# Truncation causes silent data loss and degrades output quality.
# If a variable is too large, restructure the prompt or serialise
# the data more compactly — do NOT slice it with [:N].
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.config import PILOT_JURISDICTIONS, PROMPTS_DIR, get_country_level1_dir
from pipeline.storage import save_raw_query, save_json, save_prompt, load_json, now_iso
from pipeline.parallel_runner import (
    launch_task,
    poll_all,
    load_state,
    save_state,
    _state_is_done,
)
from pipeline.logging_setup import get_logger
from level_1.prompts import (
    build_prompt_1a, build_prompt_1c,
    SCHEMA_1C,
)

logger = get_logger("jurisdiction_runner")


# ---------------------------------------------------------------------------
# Task key helpers
# ---------------------------------------------------------------------------

def _key(juris_ru: str, query: str) -> str:
    return f"{juris_ru}_{query}"


# ---------------------------------------------------------------------------
# Save functions
# ---------------------------------------------------------------------------

def _save_fn_1a(juris_ru: str, juris_en: str):
    def fn(content) -> Path:
        d = get_country_level1_dir(juris_ru)
        path = d / "1A_architecture.json"
        if isinstance(content, dict):
            text = json.dumps(content, ensure_ascii=False)
        else:
            text = str(content)
        save_raw_query(path, juris_en, "1A", text)
        return path
    return fn


def _save_fn_1c(juris_ru: str, juris_en: str):
    def fn(content) -> Path:
        d = get_country_level1_dir(juris_ru)
        path = d / "1C_venues.json"
        if isinstance(content, dict):
            data = {"jurisdiction": juris_en, **content, "retrieved_at": now_iso()}
        else:
            data = {
                "jurisdiction": juris_en,
                "query": "1C",
                "content": str(content),
                "retrieved_at": now_iso(),
            }
        save_json(path, data)
        return path
    return fn


# ---------------------------------------------------------------------------
# Launch helpers
# ---------------------------------------------------------------------------

def launch_all_1a(state: dict) -> None:
    """Launch 1A tasks for all pilot jurisdictions."""
    for j in PILOT_JURISDICTIONS:
        en = j["name_en"]
        ru = j["name_ru"]
        eu_note = j.get("eu_note")
        prompt = build_prompt_1a(en, eu_note)
        save_prompt(PROMPTS_DIR, f"1A_{ru}", prompt)

        task_key = _key(ru, "1A")
        launch_task(
            task_key=task_key,
            prompt=prompt,
            output_schema=None,  # text output
            state=state,
        )
    save_state(state)


def launch_all_1c(state: dict) -> None:
    """
    Launch 1C tasks for all pilot jurisdictions.
    Uses 1A result if available to inject regulator/market context.
    """
    for j in PILOT_JURISDICTIONS:
        en = j["name_en"]
        ru = j["name_ru"]

        # Try to read 1A result for context injection into 1C
        path_1a = get_country_level1_dir(ru) / "1A_architecture.json"
        data_1a = load_json(path_1a)
        regulator_ctx = "see regulatory architecture research"
        market_types_ctx = "see regulatory architecture research"
        if data_1a and isinstance(data_1a, dict):
            content_1a_str = data_1a.get("content", "")
            if content_1a_str:
                regulator_ctx = f"refer to 1A research: {content_1a_str}"
                market_types_ctx = f"refer to 1A research (venue types): {content_1a_str}"

        # 1C
        prompt_1c = build_prompt_1c(en, regulator_ctx, market_types_ctx)
        save_prompt(PROMPTS_DIR, f"1C_{ru}", prompt_1c)
        launch_task(
            task_key=_key(ru, "1C"),
            prompt=prompt_1c,
            output_schema=SCHEMA_1C,
            state=state,
        )

    save_state(state)


# ---------------------------------------------------------------------------
# Poll helpers
# ---------------------------------------------------------------------------

def poll_all_1a(state: dict) -> dict:
    """Poll all 1A tasks. Returns {task_key: content_or_None}."""
    tasks = []
    for j in PILOT_JURISDICTIONS:
        ru = j["name_ru"]
        en = j["name_en"]
        key = _key(ru, "1A")
        if key in state["tasks"]:
            tasks.append((key, _save_fn_1a(ru, en)))
    return poll_all(tasks, state)


def poll_all_1c(state: dict) -> dict:
    """Poll all 1C tasks."""
    tasks = []
    for j in PILOT_JURISDICTIONS:
        ru = j["name_ru"]
        en = j["name_en"]
        key = _key(ru, "1C")
        if key in state["tasks"]:
            tasks.append((key, _save_fn_1c(ru, en)))
    return poll_all(tasks, state)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def run_all():
    """Full Level 1 jurisdiction research run (1A + 1C only; 1B is imported)."""
    state = load_state()

    logger.info("=== Step 1: Launching 1A for all jurisdictions ===")
    launch_all_1a(state)

    logger.info("=== Step 2: Polling 1A until all done ===")
    poll_all_1a(state)

    logger.info("=== Step 3: Launching 1C for all jurisdictions ===")
    launch_all_1c(state)

    logger.info("=== Step 4: Polling 1C until all done ===")
    poll_all_1c(state)

    logger.info("=== Level 1 jurisdiction queries complete ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Level 1 jurisdiction runner")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--launch-1a", action="store_true")
    group.add_argument("--poll-1a", action="store_true")
    group.add_argument("--launch-1c", action="store_true")
    group.add_argument("--poll-1c", action="store_true")
    group.add_argument("--run-all", action="store_true", default=True)
    args = parser.parse_args()

    state = load_state()

    if args.launch_1a:
        launch_all_1a(state)
    elif args.poll_1a:
        poll_all_1a(state)
    elif args.launch_1c:
        launch_all_1c(state)
    elif args.poll_1c:
        poll_all_1c(state)
    else:
        run_all()
