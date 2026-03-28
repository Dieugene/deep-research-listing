#!/usr/bin/env python
"""
Diagnostic: fetch full Parallel API response for existing task_ids.
Saves complete response including output.basis (citations with URLs) to disk.

Usage:
    cd 02_src
    ..\venv\Scripts\python.exe ..\tools\diag_parallel_response.py
"""

import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
if not ENV_PATH.exists():
    print(f"ERROR: .env file not found at {ENV_PATH}", file=sys.stderr)
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv(dotenv_path=ENV_PATH)

# ---------------------------------------------------------------------------
# Task IDs to fetch
# ---------------------------------------------------------------------------
TASKS = [
    {
        "label": "1A_text",
        "run_id": "trun_a9e04426dfab4c3aa4313055e3731a58",
        "description": "France_1A (text mode)",
        "out_file": Path(__file__).resolve().parent / "diag_1a_text.json",
    },
    {
        "label": "1B_json",
        "run_id": "trun_e0411a24b2694910b6ee444f30d7ab61",
        "description": "France_1B (json mode with schema)",
        "out_file": Path(__file__).resolve().parent / "diag_1b_json.json",
    },
    {
        "label": "1C_json",
        "run_id": "trun_eaa4affd0a9b4fb29079cf5bc4a6fe2d",
        "description": "France_1C (json mode with schema)",
        "out_file": Path(__file__).resolve().parent / "diag_1c_json.json",
    },
]

# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def serialize_citation(cit) -> dict:
    """Serialize a Citation object to a plain dict."""
    try:
        return cit.model_dump()
    except AttributeError:
        pass
    try:
        return dict(cit)
    except TypeError:
        return {
            "url": getattr(cit, "url", None),
            "title": getattr(cit, "title", None),
            "excerpts": getattr(cit, "excerpts", None),
        }


def serialize_field_basis(fb) -> dict:
    """Serialize a FieldBasis object to a plain dict."""
    citations_raw = getattr(fb, "citations", None) or []
    citations = [serialize_citation(c) for c in citations_raw]
    return {
        "field": getattr(fb, "field", None),
        "reasoning": getattr(fb, "reasoning", None),
        "confidence": getattr(fb, "confidence", None),
        "citations": citations,
    }


def serialize_run(run) -> dict:
    """Serialize a TaskRun object to a plain dict."""
    try:
        return run.model_dump()
    except AttributeError:
        pass
    try:
        return dict(run)
    except TypeError:
        return {
            "run_id": getattr(run, "run_id", None),
            "status": getattr(run, "status", None),
            "processor": getattr(run, "processor", None),
            "created_at": getattr(run, "created_at", None),
            "modified_at": getattr(run, "modified_at", None),
            "is_active": getattr(run, "is_active", None),
            "error": getattr(run, "error", None),
            "warnings": getattr(run, "warnings", None),
            "metadata": getattr(run, "metadata", None),
            "task_group_id": getattr(run, "task_group_id", None),
        }


def serialize_output(output) -> dict:
    """Serialize a TaskRunTextOutput or TaskRunJsonOutput to a plain dict."""
    basis_raw = getattr(output, "basis", None) or []
    basis = [serialize_field_basis(fb) for fb in basis_raw]

    result = {
        "type": getattr(output, "type", None),
        "content": getattr(output, "content", None),
        "basis": basis,
        "beta_fields": getattr(output, "beta_fields", None),
        "output_schema": getattr(output, "output_schema", None),
    }
    return result


def serialize_result(result) -> dict:
    """Serialize a full TaskRunResult to a plain dict."""
    return {
        "output": serialize_output(result.output),
        "run": serialize_run(result.run),
    }


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------

def print_summary(label: str, description: str, data: dict) -> None:
    """Print a concise summary of a fetched result to stdout."""
    output = data.get("output", {})
    run = data.get("run", {})

    out_type = output.get("type", "unknown")
    content = output.get("content")
    basis = output.get("basis", [])

    if out_type == "text":
        content_size = f"{len(content)} chars" if isinstance(content, str) else "n/a"
    elif out_type == "json":
        content_size = f"{len(content)} top-level keys" if isinstance(content, dict) else "n/a"
    else:
        content_size = "n/a"

    print(f"\n{'='*60}")
    print(f"  {label}  —  {description}")
    print(f"{'='*60}")
    print(f"  run_id   : {run.get('run_id', 'n/a')}")
    print(f"  status   : {run.get('status', 'n/a')}")
    print(f"  processor: {run.get('processor', 'n/a')}")
    print(f"  created  : {run.get('created_at', 'n/a')}")
    print(f"  out type : {out_type}")
    print(f"  content  : {content_size}")
    print(f"  basis    : {len(basis)} entries")

    for i, fb in enumerate(basis):
        field_name = fb.get("field", "<no field>")
        citations = fb.get("citations") or []
        first_url = citations[0].get("url", "<no url>") if citations else "<no citations>"
        print(f"    [{i}] field={field_name!r}  citations={len(citations)}  first_url={first_url}")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        print("ERROR: PARALLEL_API_KEY is not set in environment / .env", file=sys.stderr)
        sys.exit(1)

    import parallel

    client = parallel.Parallel(api_key=api_key)

    out_dir = Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)

    for task in TASKS:
        label = task["label"]
        run_id = task["run_id"]
        description = task["description"]
        out_file: Path = task["out_file"]

        print(f"\nFetching {label} ({run_id}) ...")

        try:
            result = client.task_run.result(run_id)
        except parallel.NotFoundError:
            print(f"  ERROR: task_id {run_id!r} not found (404). Skipping.")
            continue
        except parallel.APIConnectionError as exc:
            print(f"  ERROR: connection failed for {run_id!r}: {exc}. Skipping.")
            continue
        except parallel.APIStatusError as exc:
            print(f"  ERROR: API returned status {exc.status_code} for {run_id!r}: {exc.message}. Skipping.")
            continue
        except Exception as exc:
            print(f"  ERROR: unexpected error for {run_id!r}: {type(exc).__name__}: {exc}. Skipping.")
            continue

        data = serialize_result(result)

        with open(out_file, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2, default=str)

        print(f"  Saved to: {out_file}")
        print_summary(label, description, data)

    print("Done.")


if __name__ == "__main__":
    main()
