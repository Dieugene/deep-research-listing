"""
Phase 2: Parameter extraction from L3 per-cell results.

Steps:
  group         — Form groups (jurisdiction × market_type × instrument_class × path_type)
  pass1         — LLM extraction of parameter structure per group
  pass2         — LLM extraction of parameter values per cell (original)
  3p-classify   — Classify UNKNOWN parameters + generate 3P drill-down prompts
  3p-run        — Execute 3P drill-down via Parallel API
  pass2-new     — New LLM extraction of parameter values per cell (with 3P integration)
  all           — Run all steps sequentially: group → pass1 → pass2 (original)
  all-extended  — Run full extended pipeline: group → pass1 → 3p-classify → 3p-run → pass2-new

Usage:
    python -m level_3.run_phase2 [--step STEP]
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.config import (
    PHASE2_LOG_FILE,
    LOGS_DIR,
    LLM_SMART_MODEL,
    COUNTRIES_DIR,
)
from pipeline.logging_setup import get_logger
from level_3.phase2_runner import (
    load_state,
    save_state,
    form_groups,
    run_pass1,
    run_pass2,
    run_all,
    run_3p_classify,
    run_3p_execute,
    run_new_pass2,
    run_all_extended,
    run_pass2_translate,
    _get_llm,
)

LOGS_DIR.mkdir(parents=True, exist_ok=True)
logger = get_logger("run_phase2", PHASE2_LOG_FILE)

STEPS = [
    "group",
    "pass1",
    "pass2",
    "3p-classify",
    "3p-run",
    "pass2-new",
    "translate",
    "all",
    "all-extended",
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 2 — parameter extraction from L3 results")
    parser.add_argument(
        "--step",
        choices=STEPS,
        default="all",
        help=(
            "Which step to run. "
            "'all' runs group+pass1+pass2 (original). "
            "'all-extended' runs group+pass1+3p-classify+3p-run+pass2-new."
        ),
    )
    args = parser.parse_args()

    state = load_state()

    if args.step == "all":
        run_all(state)
        sys.exit(0)

    if args.step == "all-extended":
        run_all_extended(state)
        sys.exit(0)

    if args.step == "group":
        form_groups(state)
        sys.exit(0)

    if args.step == "pass1":
        run_pass1(state)
        sys.exit(0)

    if args.step == "pass2":
        run_pass2(state)
        sys.exit(0)

    if args.step == "3p-classify":
        llm = _get_llm(LLM_SMART_MODEL)
        # form_groups returns the groups dict; we need it for 3p-classify
        # If groups are already formed, re-form them (idempotent) to get the dict
        groups = form_groups(state)
        run_3p_classify(groups=groups, data_root=COUNTRIES_DIR, llm=llm)
        sys.exit(0)

    if args.step == "3p-run":
        # Groups dict needed for interface consistency; pass empty dict since
        # run_3p_execute scans filesystem directly
        run_3p_execute(groups={}, data_root=COUNTRIES_DIR)
        sys.exit(0)

    if args.step == "pass2-new":
        llm = _get_llm(LLM_SMART_MODEL)
        run_new_pass2(state=state, llm=llm)
        sys.exit(0)

    if args.step == "translate":
        llm = _get_llm(LLM_SMART_MODEL)
        run_pass2_translate(llm=llm)
        sys.exit(0)
