"""
Level 1: EU Framework request.

Runs a single Deep Research task for the EU regulatory framework for
securities listing and saves the result to 03_data/supranational/eu.json.

Usage:
    python -m level_1.eu_framework           # launch task
    python -m level_1.eu_framework --poll    # poll existing task until done
    python -m level_1.eu_framework --run     # launch + poll (full run)
"""
import argparse
import sys
from pathlib import Path

# Make 02_src importable when run as a module from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.config import SUPRANATIONAL_DIR, PROMPTS_DIR
from pipeline.storage import save_text_as_json, save_prompt, load_json
from pipeline.parallel_runner import launch_task, poll_until_done, load_state, save_state
from pipeline.logging_setup import get_logger

logger = get_logger("eu_framework")

TASK_KEY = "eu_framework"

EU_PROMPT = """Research the EU regulatory framework for securities listing and
admission to trading. Focus on:

1. Key directives and regulations: MiFID II/MiFIR, Prospectus
   Regulation, Transparency Directive, Market Abuse Regulation,
   Listing Act (2024 reform).

2. For each instrument class (equities, bonds, funds, depositary
   receipts): what requirements are set at EU level vs delegated
   to national authorities. Distinction between regulated market
   admission and MTF admission.

3. Minimum harmonised requirements (free float, market cap,
   financial history, etc.).

4. National discretion: where member states can set stricter or
   different requirements.

5. Listing Act 2024: what changed, transition timeline.

6. Third-country equivalence for listing purposes.

Cite specific articles/provisions.

All information must be self-contained. Do not rely on prior context."""


def get_result_save_fn():
    """Return a closure that saves the EU framework result and returns the path."""
    def save_fn(content) -> Path:
        out_path = SUPRANATIONAL_DIR / "eu.json"
        # content may be str (text output) or dict (json output)
        if isinstance(content, dict):
            import json
            text_content = json.dumps(content, ensure_ascii=False)
        else:
            text_content = str(content)
        save_text_as_json(out_path, "EU", text_content)
        return out_path
    return save_fn


def run_launch():
    """Launch the EU framework task (idempotent if already launched)."""
    state = load_state()
    save_prompt(PROMPTS_DIR, "eu_framework", EU_PROMPT)
    task_id = launch_task(
        task_key=TASK_KEY,
        prompt=EU_PROMPT,
        output_schema=None,  # text output
        state=state,
    )
    logger.info("EU framework task launched: task_id=%s", task_id)
    return task_id


def run_poll():
    """Poll the EU framework task until done."""
    state = load_state()
    entry = state["tasks"].get(TASK_KEY)
    if not entry:
        logger.error("No EU framework task found in state. Run with --launch first.")
        sys.exit(1)

    save_fn = get_result_save_fn()
    content = poll_until_done(TASK_KEY, save_fn, state)
    if content is not None:
        logger.info("EU framework result saved.")
    else:
        # May already be done
        result_path = state["tasks"][TASK_KEY].get("result_path")
        if result_path:
            logger.info("EU framework was already done. Result at %s", result_path)
        else:
            logger.error("EU framework task failed or had no result.")
    return content


def run_full():
    """Launch + poll EU framework task."""
    run_launch()
    return run_poll()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EU Framework Deep Research task")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--launch", action="store_true", help="Launch the task only")
    group.add_argument("--poll", action="store_true", help="Poll existing task only")
    group.add_argument("--run", action="store_true", default=True, help="Launch + poll (default)")
    args = parser.parse_args()

    if args.launch:
        run_launch()
    elif args.poll:
        run_poll()
    else:
        run_full()
