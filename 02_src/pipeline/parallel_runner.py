"""
Async runner for Parallel SDK Deep Research tasks.

Pattern:
  1. Launch task → get task_id, save to state
  2. Poll every POLL_INTERVAL_SECONDS until completed/failed
  3. Save result to disk
  4. On restart: resume only tasks that are not 'done'
"""
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Optional

import parallel
from dotenv import load_dotenv

from pipeline.config import (
    LEVEL1_STATE_FILE,
    PARALLEL_PROCESSOR,
    POLL_INTERVAL_SECONDS,
)
from pipeline.storage import load_json, save_json, now_iso
from pipeline.logging_setup import get_logger

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

logger = get_logger("parallel_runner")


def _get_client() -> parallel.Parallel:
    """Create a Parallel sync client using PARALLEL_API_KEY from env."""
    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "PARALLEL_API_KEY is not set. "
            "Add it to the .env file: PARALLEL_API_KEY=<your-key>"
        )
    return parallel.Parallel(api_key=api_key)


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state(state_file: Optional[Path] = None) -> dict:
    """Load state from disk (or return empty state).

    state_file: path override (defaults to LEVEL1_STATE_FILE).
    """
    path = state_file or LEVEL1_STATE_FILE
    data = load_json(path)
    if data is None:
        return {"tasks": {}}
    return data


def save_state(state: dict, state_file: Optional[Path] = None) -> None:
    """Persist state to disk.

    state_file: path override (defaults to LEVEL1_STATE_FILE).
    """
    path = state_file or LEVEL1_STATE_FILE
    save_json(path, state)


def _state_is_done(task_entry: dict) -> bool:
    return task_entry.get("status") in ("done", "error")


# ---------------------------------------------------------------------------
# Task launch
# ---------------------------------------------------------------------------

def launch_task(
    task_key: str,
    prompt: str,
    output_schema: Optional[Any],
    state: dict,
    processor: str = PARALLEL_PROCESSOR,
    state_file: Optional[Path] = None,
) -> str:
    """
    Launch a Parallel Deep Research task.

    - If task_key already has a non-done entry in state, skip (return existing task_id).
    - Otherwise launch, save task_id to state, return task_id.

    output_schema:
        None          — text output
        "auto"        — auto-structured JSON output (structure determined by Parallel)
        dict          — explicit JSON schema for structured JSON output

    state_file: path to persist state (defaults to LEVEL1_STATE_FILE).
    """
    existing = state["tasks"].get(task_key, {})
    if existing.get("task_id") and not _state_is_done(existing):
        logger.info(
            "Task %s already launched (task_id=%s, status=%s) — skipping launch",
            task_key,
            existing["task_id"],
            existing.get("status"),
        )
        return existing["task_id"]

    if existing.get("status") == "done":
        logger.info("Task %s already done — skipping launch", task_key)
        return existing["task_id"]

    client = _get_client()

    logger.info("Launching task %s (processor=%s)", task_key, processor)
    if output_schema is None:
        run = client.task_run.create(
            input=prompt,
            processor=processor,
            task_spec={"output_schema": {"type": "text"}},
        )
    elif output_schema == "auto":
        # auto is the API default — do not pass task_spec at all (passing {"type":"auto"} explicitly is not supported)
        run = client.task_run.create(
            input=prompt,
            processor=processor,
        )
    else:
        run = client.task_run.create(
            input=prompt,
            processor=processor,
            task_spec={"output_schema": {"type": "json", "json_schema": output_schema}},
        )
    task_id = run.run_id

    state["tasks"][task_key] = {
        "task_id": task_id,
        "status": "pending",
        "result_path": None,
        "launched_at": now_iso(),
        "completed_at": None,
        "error": None,
    }
    save_state(state, state_file)
    logger.info("Task %s launched: task_id=%s", task_key, task_id)
    return task_id


# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------

def poll_until_done(
    task_key: str,
    result_save_fn,
    state: dict,
    state_file: Optional[Path] = None,
) -> Optional[Any]:
    """
    Synchronously poll a single task until it completes or fails.

    result_save_fn(content) — called with the raw output content once done.
    state_file: path override for state persistence (defaults to LEVEL1_STATE_FILE).
    Returns the content or None on error.
    """
    entry = state["tasks"][task_key]
    if entry.get("status") == "done":
        logger.info("Task %s already done (result_path=%s)", task_key, entry.get("result_path"))
        return None  # already processed

    task_id = entry["task_id"]
    client = _get_client()

    logger.info("Polling task %s (task_id=%s) ...", task_key, task_id)

    while True:
        run = client.task_run.retrieve(task_id)
        status = run.status
        logger.debug("Task %s status: %s", task_key, status)

        if status == "completed":
            # Fetch result
            result = client.task_run.result(task_id)
            output = result.output
            content = output.content
            result_path = result_save_fn(content)

            entry["status"] = "done"
            entry["result_path"] = str(result_path) if result_path else None
            entry["completed_at"] = now_iso()
            save_state(state, state_file)
            logger.info("Task %s completed. Result saved to %s", task_key, result_path)
            return content

        elif status == "failed":
            error_msg = str(run.error) if run.error else "unknown error"
            entry["status"] = "error"
            entry["error"] = error_msg
            entry["completed_at"] = now_iso()
            save_state(state, state_file)
            logger.error("Task %s FAILED: %s", task_key, error_msg)
            return None

        elif status in ("cancelled", "cancelling"):
            entry["status"] = "error"
            entry["error"] = f"Task was {status}"
            save_state(state, state_file)
            logger.error("Task %s was %s", task_key, status)
            return None

        else:
            # queued, running, action_required — keep polling
            logger.info(
                "Task %s still %s — waiting %ds before next poll",
                task_key, status, POLL_INTERVAL_SECONDS,
            )
            time.sleep(POLL_INTERVAL_SECONDS)


def poll_all(
    tasks_to_poll: list[tuple[str, Any]],
    state: dict,
    state_file: Optional[Path] = None,
) -> dict:
    """
    Poll multiple tasks sequentially until all are done.

    tasks_to_poll: list of (task_key, result_save_fn) tuples.
    state_file: path override for state persistence (defaults to LEVEL1_STATE_FILE).

    Returns dict of {task_key: content_or_None}.
    """
    results = {}
    pending = list(tasks_to_poll)

    while pending:
        next_pending = []
        for task_key, result_save_fn in pending:
            entry = state["tasks"].get(task_key, {})
            if _state_is_done(entry):
                logger.info("Task %s already done, skipping poll", task_key)
                results[task_key] = None
                continue

            task_id = entry.get("task_id")
            if not task_id:
                logger.warning("Task %s has no task_id in state, skipping", task_key)
                results[task_key] = None
                continue

            client = _get_client()
            run = client.task_run.retrieve(task_id)
            status = run.status
            logger.debug("Task %s status: %s", task_key, status)

            if status == "completed":
                result = client.task_run.result(task_id)
                content = result.output.content
                result_path = result_save_fn(content)

                entry = state["tasks"][task_key]
                entry["status"] = "done"
                entry["result_path"] = str(result_path) if result_path else None
                entry["completed_at"] = now_iso()
                save_state(state, state_file)
                logger.info("Task %s completed. Result saved to %s", task_key, result_path)
                results[task_key] = content

            elif status in ("failed", "cancelled", "cancelling"):
                error_msg = str(run.error) if run.error else f"status={status}"
                entry = state["tasks"][task_key]
                entry["status"] = "error"
                entry["error"] = error_msg
                entry["completed_at"] = now_iso()
                save_state(state, state_file)
                logger.error("Task %s FAILED: %s", task_key, error_msg)
                results[task_key] = None

            else:
                # Still running
                next_pending.append((task_key, result_save_fn))

        if next_pending:
            logger.info(
                "%d tasks still running — waiting %ds before next round",
                len(next_pending),
                POLL_INTERVAL_SECONDS,
            )
            time.sleep(POLL_INTERVAL_SECONDS)

        pending = next_pending

    return results
