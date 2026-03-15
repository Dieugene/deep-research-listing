"""
Re-harvest Parallel API results to add basis/citations to existing raw files.

For each completed task in all state files, fetches full output.model_dump()
from Parallel API and overwrites the raw file with:
  {
    ...existing metadata...,
    "parallel_output": {
      "content": ...,
      "basis": [{"field": ..., "citations": [{"url": ..., "title": ...}]}]
    }
  }

Idempotent: skips files that already have "parallel_output" key.

Usage:
    cd D:\\_workspace\\deep-research-listing
    venv\\Scripts\\python.exe tools/reharvest_parallel.py [--dry-run] [--state LEVEL1|LEVEL2|LEVEL3|LEVEL3_V2|LEVEL4|ALL]
"""

import argparse
import io
import json
import os
import sys
from pathlib import Path

# Force UTF-8 output on Windows (avoids cp1251 UnicodeEncodeError for task keys with non-Latin chars)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import parallel
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=REPO_ROOT / ".env")

LOGS_DIR = REPO_ROOT / "04_logs"

STATE_FILES = {
    "LEVEL1":    LOGS_DIR / "level1_state.json",
    "LEVEL2":    LOGS_DIR / "level2_state.json",
    "LEVEL3":    LOGS_DIR / "level3_state.json",
    "LEVEL3_V2": LOGS_DIR / "level3_v2_state.json",
    "LEVEL4":    LOGS_DIR / "level4_state.json",
}

# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def collect_tasks(level_names: list[str]) -> list[dict]:
    """
    Return a flat list of dicts:
      {level, task_key, task_id, result_path}
    Only includes tasks that are 'done' and have a result_path.
    """
    collected = []
    for level in level_names:
        state_path = STATE_FILES[level]
        if not state_path.exists():
            print(f"  [WARN] State file not found, skipping: {state_path}")
            continue
        state = load_json(state_path)
        tasks = state.get("tasks", {})
        for task_key, task in tasks.items():
            if task.get("status") != "done":
                continue
            result_path = task.get("result_path")
            if not result_path:
                continue
            task_id = task.get("task_id")
            if not task_id:
                continue
            collected.append({
                "level": level,
                "task_key": task_key,
                "task_id": task_id,
                "result_path": Path(result_path),
            })
    return collected


def run_reharvest(level_names: list[str], dry_run: bool) -> None:
    print(f"Collecting tasks from: {', '.join(level_names)}")
    tasks = collect_tasks(level_names)
    total = len(tasks)
    print(f"Found {total} completed tasks with result paths.\n")

    if total == 0:
        print("Nothing to process.")
        return

    client = parallel.Parallel(api_key=os.environ["PARALLEL_API_KEY"])

    updated = 0
    already_new = 0
    errors = 0

    for idx, task in enumerate(tasks, start=1):
        label = f"[{idx}/{total}]"
        task_key = task["task_key"]
        task_id = task["task_id"]
        result_path = task["result_path"]
        level = task["level"]

        # --- Check if raw file exists ---
        if not result_path.exists():
            print(f"{label} SKIP  {level}:{task_key} — result_path not found: {result_path}")
            errors += 1
            continue

        # --- Load raw file ---
        try:
            raw = load_json(result_path)
        except Exception as exc:
            print(f"{label} ERROR {level}:{task_key} — could not read raw file: {exc}")
            errors += 1
            continue

        # --- Idempotency check ---
        if "parallel_output" in raw:
            print(f"{label} SKIP  {level}:{task_key} — already has parallel_output")
            already_new += 1
            continue

        print(f"{label} Fetching {level}:{task_key} (task_id={task_id})...", end=" ", flush=True)

        if dry_run:
            print("[DRY-RUN]")
            updated += 1
            continue

        # --- Fetch from Parallel API ---
        try:
            result = client.task_run.result(task_id)
            output_data = result.output.model_dump()
        except Exception as exc:
            print(f"ERROR — {exc}")
            errors += 1
            continue

        # --- Merge and save ---
        try:
            raw["parallel_output"] = output_data
            save_json(result_path, raw)
            print("OK")
            updated += 1
        except Exception as exc:
            print(f"ERROR writing file — {exc}")
            errors += 1
            continue

    # --- Summary ---
    print()
    if dry_run:
        print(f"Done (dry-run): {updated} would be updated, {already_new} already_new_format, {errors} errors")
    else:
        print(f"Done: {updated} updated, {already_new} already_new_format, {errors} errors")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-harvest Parallel API results to add basis/citations to raw files."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be done without writing any files.",
    )
    parser.add_argument(
        "--state",
        default="ALL",
        choices=["LEVEL1", "LEVEL2", "LEVEL3", "LEVEL3_V2", "LEVEL4", "ALL"],
        help="Which state file(s) to process (default: ALL).",
    )
    args = parser.parse_args()

    if args.state == "ALL":
        level_names = list(STATE_FILES.keys())
    else:
        level_names = [args.state]

    if args.dry_run:
        print("=== DRY-RUN MODE — no files will be written ===\n")

    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        print("ERROR: PARALLEL_API_KEY not set in environment / .env file.", file=sys.stderr)
        sys.exit(1)

    run_reharvest(level_names, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
