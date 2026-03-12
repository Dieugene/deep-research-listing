# Диагностический модуль — не является частью основного пайплайна.
# Воспроизводит Pass 1 вызовы Phase 2 для 5 групп, которые стабильно падали с Connection error.

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — must come before project imports
# ---------------------------------------------------------------------------

_TOOLS_DIR = Path(__file__).resolve().parent          # 02_src/tools/
_SRC_DIR = _TOOLS_DIR.parent                          # 02_src/
_PROJECT_ROOT = _SRC_DIR.parent                       # project root

sys.path.insert(0, str(_SRC_DIR))

from dotenv import load_dotenv
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

# ---------------------------------------------------------------------------
# Imports from phase2_runner (models, constants, prompt builder internals)
# ---------------------------------------------------------------------------

from level_3.phase2_runner import (
    Pass1Result,
    ParameterEntry,
    LLM_SMART_MODEL,
    PARAM_CHECKLISTS,
    COUNTRIES_DIR,
)
from pipeline.storage import load_json
from pipeline.config import get_country_level3_dir

# ---------------------------------------------------------------------------
# 5 failing groups — hardcoded
# ---------------------------------------------------------------------------

FAILING_GROUPS = [
    {
        "group_id": "United_Kingdom_regulated_market_equity_distinct",
        "name_ru": "Великобритания",
    },
    {
        "group_id": "United_Kingdom_regulated_market_equity_standard",
        "name_ru": "Великобритания",
    },
    {
        "group_id": "Hong_Kong_regulated_market_bond_standard",
        "name_ru": "Гонконг",
    },
    {
        "group_id": "Hong_Kong_regulated_market_equity_distinct",
        "name_ru": "Гонконг",
    },
    {
        "group_id": "Hong_Kong_regulated_market_equity_standard",
        "name_ru": "Гонконг",
    },
]

# ---------------------------------------------------------------------------
# Output directory for saved prompts
# ---------------------------------------------------------------------------

DIAG_PROMPTS_DIR = _TOOLS_DIR / "diag_prompts"

# ---------------------------------------------------------------------------
# Duplicated prompt-building helpers (private in phase2_runner — cannot import)
# ---------------------------------------------------------------------------

def _serialize_cell_data(cell_id: str, qt: str, content: dict) -> str:
    """Serialize one (cell, query_type) result to structured text."""
    lines = [f"=== Cell: {cell_id} | Query: {qt} ==="]
    tier_name = content.get("tier_name", "")
    if tier_name:
        lines.append(f"Tier: {tier_name}\n")
    for key, val in content.items():
        if key == "tier_name":
            continue
        if isinstance(val, dict) and "description" in val:
            lines.append(f"[{key}]")
            lines.append(f"  description: {val.get('description', '')}")
            lines.append(f"  source: {val.get('source', '')}")
            lines.append("")
        elif isinstance(val, dict):
            lines.append(f"[{key}]: {json.dumps(val, ensure_ascii=False)}")
            lines.append("")
        elif val is not None:
            lines.append(f"[{key}]: {val}")
            lines.append("")
    return "\n".join(lines)


def _build_pass1_prompt(
    group_id: str,
    name_ru: str,
    market_type: str,
    instrument_class: str,
    admission_path_type: str,
    cells_data: list[dict],
) -> str:
    """Exact copy of phase2_runner._build_pass1_prompt."""
    cell_lines = []
    for cd in cells_data:
        cell_lines.append(
            f"  - cell_id: {cd['cell_id']} | venue: {cd['venue_key']} "
            f"| tier: {cd['tier']} | data available: {cd['valid_qts']}"
        )
    cell_list_str = "\n".join(cell_lines)

    research_parts = []
    for cd in cells_data:
        for qt, content in cd["content_by_qt"].items():
            research_parts.append(_serialize_cell_data(cd["cell_id"], qt, content))
    research_str = "\n\n".join(research_parts)

    checklist = PARAM_CHECKLISTS.get(instrument_class, [])
    checklist_str = "\n".join(f"  {pid}: {pname}" for pid, pname in checklist)

    return f"""You are analyzing the admission parameter framework for a group of venues
within the same jurisdiction, market type, and instrument class.

JURISDICTION: {name_ru}
MARKET TYPE: {market_type}
INSTRUMENT CLASS: {instrument_class}
ADMISSION PATH TYPE: {admission_path_type}
VENUES/CELLS IN THIS GROUP:
{cell_list_str}

RESEARCH DATA FROM ALL CELLS IN THIS GROUP:
{research_str}

---
TASK: Extract the COMMON parameter framework for this group.

PARAMETER CHECKLIST for {instrument_class}:
{checklist_str}

For each parameter in the checklist:
- If the parameter APPLIES to this group: describe its structure using the
  6-question template below. Where parameter VALUES differ between venues
  or tiers within the group — note the range, but focus on STRUCTURAL
  description.
- If the parameter does NOT APPLY: status="not_applicable" with brief note.
- If data does not contain information: status="data_not_found".

PARAMETER DESCRIPTION TEMPLATE (answer all 6 for each found parameter):
1. WHAT IS ESTABLISHED? Numeric threshold, qualitative criterion, or combination.
   In what units (%, count, monetary amount). If monetary — in what currency.
2. HOW IS IT CALCULATED? What is included, what is excluded. Who verifies.
3. ARE THERE ALTERNATIVES? Either/or options.
4. DOES IT VARY? By company size, tier, issuer type, sub-class (e.g. professional vs retail),
   market maker presence.
5. IS IT LINKED TO OTHER PARAMETERS? Bundles, dependencies.
6. SOURCE. Specific rule, section, chapter.

LIFECYCLE PHASES — for each found parameter, specify which phase the value applies to:
- ADMISSION: threshold for initial admission
- CONTINUING: threshold for maintaining listing
- REMOVAL: threshold triggering suspension or delisting
If values differ by phase — describe each separately.

UNKNOWN PARAMETERS:
If you find admission requirements not matching any checklist parameter — report them
as additional_parameters with the same 6-question description. Set parameter_id to
"ADDITIONAL_1", "ADDITIONAL_2", etc.

Set group_id="{group_id}" and instrument_class="{instrument_class}" in your response."""


# ---------------------------------------------------------------------------
# Main diagnostic runner
# ---------------------------------------------------------------------------

def main(args) -> None:
    # --- Environment info ---
    base_url = os.environ.get("OPENAI_BASE_URL", "(not set — using OpenAI default)")
    api_key_raw = os.environ.get("OPENAI_API_KEY", "")
    api_key_masked = api_key_raw[:10] + "..." if len(api_key_raw) >= 10 else "(short/missing)"

    print("=" * 70)
    print("DIAG: Phase 2 Pass 1 — 5 failing groups")
    print("=" * 70)
    print(f"OPENAI_BASE_URL : {base_url}")
    print(f"OPENAI_API_KEY  : {api_key_masked}")
    print(f"LLM model       : {LLM_SMART_MODEL}")
    print("=" * 70)
    print()

    # --- Create output dir ---
    DIAG_PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Prompt output dir: {DIAG_PROMPTS_DIR}")
    print()

    # --- LLM / chain (exact same init as phase2_runner) ---
    llm = ChatOpenAI(model=LLM_SMART_MODEL, api_key=os.environ["OPENAI_API_KEY"], temperature=0)
    chain = llm.with_structured_output(Pass1Result, method="function_calling")

    # --- Build work items ---
    work_items = []

    for entry in FAILING_GROUPS:
        group_id = entry["group_id"]
        name_ru = entry["name_ru"]

        meta_path = COUNTRIES_DIR / name_ru / "level_3" / "_groups" / group_id / "group_meta.json"
        group_meta = load_json(meta_path)
        if not group_meta:
            print(f"[ERROR] group_meta.json not found for {group_id} — skipping")
            continue

        market_type = group_meta["market_type"]
        instrument_class = group_meta["instrument_class"]
        admission_path_type = group_meta["admission_path_type"]
        gname_ru = group_meta["name_ru"]

        cells_data = []
        for cell_info in group_meta["cells"]:
            cell_id = cell_info["cell_id"]
            venue_key = cell_info["venue_key"]
            tier = cell_info["tier"]
            valid_qts = cell_info["valid_qts"]

            content_by_qt = {}
            for qt in valid_qts:
                raw_path = get_country_level3_dir(gname_ru, venue_key) / cell_id / f"{qt}_raw.json"
                raw_data = load_json(raw_path)
                if raw_data:
                    content_by_qt[qt] = raw_data.get("content", {})
                else:
                    print(f"  [WARN] Raw data missing: {cell_id} / {qt}")

            if content_by_qt:
                cells_data.append({
                    "cell_id": cell_id,
                    "venue_key": venue_key,
                    "tier": tier,
                    "valid_qts": list(content_by_qt.keys()),
                    "content_by_qt": content_by_qt,
                })

        if not cells_data:
            print(f"[ERROR] No cell data for group {group_id} — skipping")
            continue

        prompt = _build_pass1_prompt(
            group_id=group_id,
            name_ru=gname_ru,
            market_type=market_type,
            instrument_class=instrument_class,
            admission_path_type=admission_path_type,
            cells_data=cells_data,
        )

        # Save prompt to file before any API call
        prompt_file = DIAG_PROMPTS_DIR / f"{group_id}_pass1_prompt.txt"
        prompt_file.write_text(prompt, encoding="utf-8")
        print(f"[PROMPT SAVED] {prompt_file.name}  ({len(prompt)} chars)")

        work_items.append({
            "group_id": group_id,
            "prompt": prompt,
        })

    if args.save_only:
        print("\n[--save-only] Prompts saved. Skipping API call.")
        return

    if not work_items:
        print("\n[ABORT] No work items to process.")
        return

    print(f"\nPrepared {len(work_items)} prompts. Starting batch call...")
    print(f"max_concurrency=50, return_exceptions=True")
    print()

    # --- Batch call (exact same as phase2_runner.run_pass1) ---
    prompts = [item["prompt"] for item in work_items]

    t_start = time.perf_counter()
    results = chain.batch(
        [[HumanMessage(content=p)] for p in prompts],
        config={"max_concurrency": 50},
        return_exceptions=True,
    )
    t_elapsed = time.perf_counter() - t_start

    print(f"Batch call finished in {t_elapsed:.2f}s")
    print()

    # --- Report results ---
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)

    for item, result in zip(work_items, results):
        group_id = item["group_id"]
        if isinstance(result, Exception):
            exc_type = type(result).__name__
            print(f"[FAIL]  {group_id}")
            print(f"        Exception type : {exc_type}")
            print(f"        Message        : {result}")
        else:
            n_params = len(result.parameters)
            n_add = len(result.additional_parameters)
            print(f"[OK]    {group_id}")
            print(f"        parameters={n_params}  additional={n_add}")
        print()

    print(f"Total wall time: {t_elapsed:.2f}s")
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--save-only", action="store_true", help="Save prompts to disk and exit without making API calls")
    args = parser.parse_args()
    main(args)
