"""
Phase 2: Parameter extraction from L3 per-cell validation results.

Two LLM passes:
  Pass 1 (per group): Extract parameter *structure* — which parameters apply
                      and how they are constructed (common framework).
  Pass 2 (per cell):  Extract specific *values* for each cell using Pass 1 results.

Additional steps:
  3P-classify (per group): Classify UNKNOWN parameters + generate 3P drill-down prompts.
  3P-execute  (per group): Run 3P drill-down via Parallel API, save raw results.
  Pass 2 new  (per cell):  Extract specific values using Pass 1 + 3P results, new schema.

Groups are keyed by (name_ru, market_type, instrument_class, admission_path_type).
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional, Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from pipeline.config import (
    LLM_SMART_MODEL,
    COUNTRIES_DIR,
    PHASE2_STATE_FILE,
    PHASE2_LOG_FILE,
    PILOT_VENUES,
    JURISDICTION_BY_RU,
    get_country_level2_dir,
    get_country_level3_dir,
)
from pipeline.storage import load_json, save_json, now_iso
from pipeline.logging_setup import get_logger

logger = get_logger("phase2", PHASE2_LOG_FILE)


# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------

def _get_llm(model: str = LLM_SMART_MODEL) -> ChatOpenAI:
    return ChatOpenAI(model=model, api_key=os.environ["OPENAI_API_KEY"], temperature=0)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ParameterEntry(BaseModel):
    parameter_id: str        # "П01", "П22", or "ADDITIONAL_1" etc.
    parameter_name: str
    status: str              # "found" | "not_applicable" | "data_not_found"
    description: str         # 6-question text; empty string if not found/not applicable
    note: str = ""           # brief explanation for not_applicable; empty otherwise


class Pass1Result(BaseModel):
    group_id: str
    instrument_class: str
    parameters: list[ParameterEntry]
    additional_parameters: list[ParameterEntry]


class ParameterValue(BaseModel):
    parameter_id: str
    admission_value: str     # "not_applicable" or "not_found" if so
    continuing_value: str
    removal_value: str
    notes: str


class Pass2Result(BaseModel):
    cell_id: str
    group_id: str
    parameter_values: list[ParameterValue]


class Pass2CellParameterValue(BaseModel):
    parameter_id: str
    parameter_name: str
    lifecycle_phase: str = ""
    value: str = ""
    calculation_methodology: str = ""
    alternatives: str = ""
    variations: str = ""
    linkages: list[str] = []
    source: str = ""
    drill_down_applied: bool = False
    status: str = "not_found"  # found | not_found | not_applicable
    note: str = ""


class Pass2CellResult(BaseModel):
    parameter_values: list[Pass2CellParameterValue]


class UnknownClassification(BaseModel):
    original_id: str = ""
    original_name: str = ""
    category: str = ""   # "A" | "B" | "C"
    reason: str = ""
    mapped_to_id: Optional[str] = None
    candidate_id: Optional[str] = None
    lifecycle_phases: Optional[str] = None


class DrillDownEvaluation(BaseModel):
    parameter_id: str = ""
    parameter_name: str = ""
    needs_drill_down: bool = False
    reason: str = ""
    prompt: Optional[str] = None


class ThreePParameterSchemaItem(BaseModel):
    parameter_id: str = ""
    parameter_name: str = ""
    lifecycle_phases: str = ""


class ThreePOutputSchema(BaseModel):
    parameters: list[ThreePParameterSchemaItem] = []


class ThreePClassifyResult(BaseModel):
    group_id: str = ""
    unknown_classifications: list[UnknownClassification] = []
    drill_down_evaluations: list[DrillDownEvaluation] = []
    three_p_required: bool = False
    three_p_combined_prompt: Optional[str] = None
    three_p_schema: Optional[ThreePOutputSchema] = None


# ---------------------------------------------------------------------------
# Checklists
# ---------------------------------------------------------------------------

PARAM_CHECKLISTS = {
    "equity": [
        ("П01", "Free float / Public float / Shares in public hands"),
        ("П02", "Minimum market capitalization"),
        ("П03", "Minimum number of shareholders / holders"),
        ("П04", "Minimum share price / Bid price"),
        ("П05", "Minimum shares outstanding"),
        ("П06", "Minimum trading volume"),
        ("П07", "Track record / Operating history / Financial history"),
        ("П08", "Profit / Earnings test"),
        ("П09", "Net tangible assets / Shareholders' equity"),
        ("П10", "Revenue requirement"),
        ("П11", "Working capital requirement"),
        ("П12", "Corporate governance standards"),
        ("П13", "Auditor / Accounting standards"),
        ("П14", "Sponsor / Nomad / Listing agent"),
        ("П15", "Market maker / Liquidity provider"),
        ("П16", "Prospectus / Admission document"),
        ("П17", "Lock-up / Lock-in period"),
        ("П18", "Escrow restrictions"),
    ],
    "bond": [
        ("П07", "Track record / Operating history"),
        ("П09", "Net assets / Equity requirements"),
        ("П13", "Accounting standards / Auditor"),
        ("П14", "Sponsor / Listing agent"),
        ("П16", "Prospectus / Listing particulars"),
        ("П19", "Minimum issue size / Minimum denomination"),
        ("П20", "Minimum denomination / Minimum lot size"),
        ("П21", "Credit rating requirement"),
        ("П22", "Minimum maturity / Remaining term"),
        ("П23", "Trustee / Fiscal agent / Paying agent"),
    ],
    "fund": [
        ("П01", "Free float / Units in public hands"),
        ("П03", "Minimum number of unitholders"),
        ("П07", "Track record of fund / manager"),
        ("П14", "Sponsor / Listing agent"),
        ("П15", "Market maker / Authorized participant (for ETF)"),
        ("П16", "Prospectus / Key investor document"),
        ("П24", "Minimum NAV / Minimum fund size / Minimum AUM"),
        ("П25", "Diversification requirements"),
        ("П26", "Fund manager authorization / licensing"),
        ("П27", "Custodian / Depositary requirements"),
    ],
    "depositary_receipt": [
        ("П01", "Free float / Public float of DRs"),
        ("П02", "Minimum market capitalization of DRs / Underlying"),
        ("П03", "Minimum number of DR holders"),
        ("П16", "Prospectus"),
        ("П28", "Primary listing requirement for underlying security"),
        ("П29", "Recognized jurisdiction / Equivalence"),
        ("П30", "Depositary bank requirements"),
    ],
}


# ---------------------------------------------------------------------------
# Slug helper
# ---------------------------------------------------------------------------

def _slugify(s: str) -> str:
    """Replace spaces and slashes with underscores; keep ASCII characters only."""
    result = []
    for ch in s:
        if ch in (" ", "/", "\\", "-"):
            result.append("_")
        elif ch.isascii() and (ch.isalnum() or ch == "_"):
            result.append(ch)
        # Drop non-ASCII and other special characters
    return "".join(result).strip("_")


def _make_group_id(name_en: str, market_type: str, instrument_class: str, admission_path_type: str) -> str:
    """Build ASCII-safe group_id from jurisdiction English name and group key parts."""
    parts = [
        _slugify(name_en),
        _slugify(market_type),
        _slugify(instrument_class),
        _slugify(admission_path_type),
    ]
    return "_".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Content serializer
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


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _build_pass1_prompt(
    group_id: str,
    name_ru: str,
    market_type: str,
    instrument_class: str,
    admission_path_type: str,
    cells_data: list[dict],
) -> str:
    """
    Build Pass 1 prompt for a group.

    cells_data items: {
        "cell_id": str,
        "venue_key": str,
        "tier": str,
        "valid_qts": list[str],
        "content_by_qt": {qt: content_dict},
    }
    """
    # Cell list header
    cell_lines = []
    for cd in cells_data:
        cell_lines.append(
            f"  - cell_id: {cd['cell_id']} | venue: {cd['venue_key']} "
            f"| tier: {cd['tier']} | data available: {cd['valid_qts']}"
        )
    cell_list_str = "\n".join(cell_lines)

    # Serialized research data
    research_parts = []
    for cd in cells_data:
        for qt, content in cd["content_by_qt"].items():
            research_parts.append(_serialize_cell_data(cd["cell_id"], qt, content))
    research_str = "\n\n".join(research_parts)

    # Checklist
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


def _build_pass2_prompt(
    cell_id: str,
    venue_key: str,
    tier: str,
    instrument_class: str,
    pass1_result: Pass1Result,
    content_by_qt: dict,
) -> str:
    """
    Build Pass 2 prompt for a single cell.

    content_by_qt: {qt: content_dict} for valid qts only.
    """
    # Framework parameters (found only)
    framework_parts = []
    for param in pass1_result.parameters:
        if param.status == "found":
            framework_parts.append(
                f"{param.parameter_id}: {param.parameter_name}\n{param.description}"
            )
    framework_str = "\n\n".join(framework_parts) if framework_parts else "(no parameters found in group analysis)"

    # Cell research data
    research_parts = []
    for qt, content in content_by_qt.items():
        research_parts.append(_serialize_cell_data(cell_id, qt, content))
    research_str = "\n\n".join(research_parts)

    return f"""Given the parameter framework below (extracted for this jurisdiction, market type,
and instrument class), extract the specific threshold VALUES for this venue/tier.

PARAMETER FRAMEWORK (from group analysis):
{framework_str}

CELL: {cell_id} | venue: {venue_key} | tier: {tier} | instrument_class: {instrument_class}

CELL RESEARCH DATA:
{research_str}

---
TASK: For each parameter in the framework:
- Report the specific numeric value or qualitative criterion for THIS venue/tier.
- If the value differs by lifecycle phase (admission / continuing / removal) — report each.
- If a parameter from the framework does not apply to this specific venue/tier — state why.
- Do NOT re-describe parameter structure — only report values.

Set parameter_id to match the framework (e.g., "П01", "П07", "ADDITIONAL_1").
Set cell_id="{cell_id}" and group_id="{pass1_result.group_id}" in your response."""


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    data = load_json(PHASE2_STATE_FILE)
    return data if data is not None else {
        "groups_formed": False,
        "pass1_complete": False,
        "pass2_complete": False,
    }


def save_state(state: dict) -> None:
    save_json(PHASE2_STATE_FILE, state)


# ---------------------------------------------------------------------------
# Group formation
# ---------------------------------------------------------------------------

def form_groups(state: dict) -> dict:
    """
    Build group definitions from all pilot venues and save group_meta.json files.

    Returns groups dict:
        {group_id: {
            "name_ru", "name_en", "market_type", "instrument_class",
            "admission_path_type",
            "cells": [{"cell_id", "venue_key", "tier", "valid_qts", "excluded_qts"}]
        }}
    """
    groups: dict = {}

    for venue in PILOT_VENUES:
        venue_key = venue["venue_key"]
        name_ru = venue["name_ru"]
        market_type = venue["market_type"]

        # Look up English name for ASCII group_id
        jur_config = JURISDICTION_BY_RU.get(name_ru, {})
        name_en = jur_config.get("name_en", name_ru)

        cells_path = get_country_level2_dir(name_ru, venue_key) / "cells_list.json"
        cells_data = load_json(cells_path)
        if not cells_data:
            logger.warning("cells_list.json not found for %s — skipping", venue_key)
            continue
        cells = cells_data.get("cells", [])

        for cell in cells:
            cell_id = cell.get("cell_id", "")
            instrument_class = cell.get("instrument_class", "")
            tier = cell.get("tier", "")

            # Determine admission_path_type
            if cell.get("admission_path") == "trading_only":
                admission_path_type = "att"
            elif cell.get("distinct_regime") is True:
                admission_path_type = "distinct"
            else:
                admission_path_type = "standard"

            # Determine valid query types
            cell_dir = get_country_level3_dir(name_ru, venue_key) / cell_id
            valid_qts = []
            excluded_qts = []
            for qt in ("3A", "3B", "3C"):
                val_path = cell_dir / f"{qt}_validation.json"
                val_data = load_json(val_path)
                if val_data is None:
                    excluded_qts.append(qt)
                    continue
                status = val_data.get("validation_status", "")
                if status in ("green", "yellow"):
                    valid_qts.append(qt)
                else:
                    excluded_qts.append(qt)

            if not valid_qts:
                logger.info(
                    "[CELL_SKIPPED] %s — all query types red or missing", cell_id
                )
                continue

            group_id = _make_group_id(name_en, market_type, instrument_class, admission_path_type)

            if group_id not in groups:
                groups[group_id] = {
                    "group_id": group_id,
                    "name_ru": name_ru,
                    "name_en": name_en,
                    "market_type": market_type,
                    "instrument_class": instrument_class,
                    "admission_path_type": admission_path_type,
                    "cells": [],
                }

            groups[group_id]["cells"].append({
                "cell_id": cell_id,
                "venue_key": venue_key,
                "tier": tier,
                "valid_qts": valid_qts,
                "excluded_qts": excluded_qts,
            })

    # Save group metadata
    for group_id, group_meta in groups.items():
        name_ru = group_meta["name_ru"]
        meta_path = (
            COUNTRIES_DIR / name_ru / "level_3" / "_groups" / group_id / "group_meta.json"
        )
        save_json(meta_path, group_meta)
        n_cells = len(group_meta["cells"])
        n_qts = sum(len(c["valid_qts"]) for c in group_meta["cells"])
        logger.info("[GROUP] %s: %d cells (%d qts)", group_id, n_cells, n_qts)

    if not groups:
        logger.warning("No groups formed — check that validation files exist")
    else:
        logger.info("Total groups formed: %d", len(groups))

    state["groups_formed"] = True
    save_state(state)
    return groups


# ---------------------------------------------------------------------------
# Pass 1: Extract parameter structure per group
# ---------------------------------------------------------------------------

def run_pass1(state: dict) -> None:
    """
    For each formed group, build a Pass 1 prompt and run a single chain.batch()
    to extract the common parameter framework. Save results as pass1.json.
    """
    llm = _get_llm(LLM_SMART_MODEL)
    chain = llm.with_structured_output(Pass1Result, method="function_calling")
    logger.info("Starting Phase 2 Pass 1 (parameter structure extraction)")

    # Collect all group directories across all jurisdictions
    work_items = []

    # Deduplicate by name_ru — multiple venues share the same jurisdiction _groups dir
    seen_name_ru: set[str] = set()
    for venue in PILOT_VENUES:
        name_ru = venue["name_ru"]
        if name_ru in seen_name_ru:
            continue
        seen_name_ru.add(name_ru)
        groups_base = COUNTRIES_DIR / name_ru / "level_3" / "_groups"
        if not groups_base.exists():
            continue
        for group_dir in sorted(groups_base.iterdir()):
            if not group_dir.is_dir():
                continue
            group_id = group_dir.name
            pass1_path = group_dir / "pass1.json"
            if pass1_path.exists():
                logger.info("[SKIP] pass1.json already exists for group %s", group_id)
                continue

            meta_path = group_dir / "group_meta.json"
            group_meta = load_json(meta_path)
            if not group_meta:
                logger.warning("group_meta.json missing for group %s — skipping", group_id)
                continue

            gname_ru = group_meta["name_ru"]
            market_type = group_meta["market_type"]
            instrument_class = group_meta["instrument_class"]
            admission_path_type = group_meta["admission_path_type"]

            # Load cell data for all valid (cell, qt) pairs in this group
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
                        logger.warning(
                            "Raw data missing for %s / %s — skipping qt in Pass 1", cell_id, qt
                        )

                if content_by_qt:
                    cells_data.append({
                        "cell_id": cell_id,
                        "venue_key": venue_key,
                        "tier": tier,
                        "valid_qts": list(content_by_qt.keys()),
                        "content_by_qt": content_by_qt,
                    })

            if not cells_data:
                logger.warning("[GROUP_SKIPPED] %s — no cell data available", group_id)
                continue

            prompt = _build_pass1_prompt(
                group_id=group_id,
                name_ru=gname_ru,
                market_type=market_type,
                instrument_class=instrument_class,
                admission_path_type=admission_path_type,
                cells_data=cells_data,
            )
            work_items.append({
                "group_id": group_id,
                "pass1_path": pass1_path,
                "instrument_class": instrument_class,
                "prompt": prompt,
            })

    if not work_items:
        logger.info("No groups need Pass 1 processing — all done or no groups found")
        state["pass1_complete"] = True
        save_state(state)
        return

    logger.info("Running Pass 1 batch for %d groups", len(work_items))
    prompts = [item["prompt"] for item in work_items]
    results = chain.batch(
        [[HumanMessage(content=p)] for p in prompts],
        config={"max_concurrency": 50},
        return_exceptions=True,
    )

    # Save results
    for item, result in zip(work_items, results):
        group_id = item["group_id"]
        pass1_path = item["pass1_path"]
        instrument_class = item["instrument_class"]

        if isinstance(result, Exception):
            logger.error("Pass 1 LLM call failed for group %s: %s", group_id, result)
            continue

        pass1_result: Pass1Result = result
        save_json(pass1_path, pass1_result.model_dump())
        logger.info("[PASS1_SAVED] %s (%d params)", group_id, len(pass1_result.parameters))

        # Warn if high data_not_found rate
        total = len(pass1_result.parameters)
        if total > 0:
            not_found_count = sum(
                1 for p in pass1_result.parameters if p.status == "data_not_found"
            )
            ratio = not_found_count / total
            if ratio > 0.7:
                logger.warning(
                    "[WARNING] HIGH_DATA_NOT_FOUND: group %s — %.0f%% parameters have no data",
                    group_id, ratio * 100,
                )

        # Log unknown parameters
        for add_param in pass1_result.additional_parameters:
            logger.info(
                "[UNKNOWN_PARAM] group %s — %s: %s",
                group_id, add_param.parameter_id, add_param.parameter_name,
            )

    state["pass1_complete"] = True
    save_state(state)
    logger.info("Phase 2 Pass 1 complete")


# ---------------------------------------------------------------------------
# Pass 2: Extract parameter values per cell
# ---------------------------------------------------------------------------

def run_pass2(state: dict) -> None:
    """
    For each group with a pass1.json, for each cell in the group, build a Pass 2
    prompt and run a single chain.batch() to extract specific parameter values.
    Save results as params.json per cell.
    """
    llm = _get_llm(LLM_SMART_MODEL)
    chain = llm.with_structured_output(Pass2Result, method="function_calling")
    logger.info("Starting Phase 2 Pass 2 (parameter value extraction)")

    work_items = []

    # Deduplicate by name_ru — multiple venues share the same jurisdiction _groups dir
    seen_name_ru: set[str] = set()
    for venue in PILOT_VENUES:
        name_ru = venue["name_ru"]
        if name_ru in seen_name_ru:
            continue
        seen_name_ru.add(name_ru)
        groups_base = COUNTRIES_DIR / name_ru / "level_3" / "_groups"
        if not groups_base.exists():
            continue
        for group_dir in sorted(groups_base.iterdir()):
            if not group_dir.is_dir():
                continue
            group_id = group_dir.name
            pass1_path = group_dir / "pass1.json"
            if not pass1_path.exists():
                logger.info("[SKIP] No pass1.json for group %s — skipping Pass 2", group_id)
                continue

            pass1_data = load_json(pass1_path)
            if not pass1_data:
                logger.warning("pass1.json empty for group %s — skipping", group_id)
                continue

            try:
                pass1_result = Pass1Result(**pass1_data)
            except Exception as exc:
                logger.error("Failed to parse pass1.json for group %s: %s", group_id, exc)
                continue

            meta_path = group_dir / "group_meta.json"
            group_meta = load_json(meta_path)
            if not group_meta:
                logger.warning("group_meta.json missing for group %s — skipping", group_id)
                continue

            gname_ru = group_meta["name_ru"]
            instrument_class = group_meta["instrument_class"]

            for cell_info in group_meta["cells"]:
                cell_id = cell_info["cell_id"]
                venue_key = cell_info["venue_key"]
                tier = cell_info["tier"]
                valid_qts = cell_info["valid_qts"]

                cell_dir = get_country_level3_dir(gname_ru, venue_key) / cell_id
                params_path = cell_dir / "params.json"
                if params_path.exists():
                    logger.info("[SKIP] params.json already exists for cell %s", cell_id)
                    continue

                # Load cell content for valid qts
                content_by_qt = {}
                for qt in valid_qts:
                    raw_path = cell_dir / f"{qt}_raw.json"
                    raw_data = load_json(raw_path)
                    if raw_data:
                        content_by_qt[qt] = raw_data.get("content", {})
                    else:
                        logger.warning(
                            "Raw data missing for %s / %s — skipping qt in Pass 2", cell_id, qt
                        )

                if not content_by_qt:
                    logger.warning("[CELL_SKIPPED] %s — no raw data available for Pass 2", cell_id)
                    continue

                prompt = _build_pass2_prompt(
                    cell_id=cell_id,
                    venue_key=venue_key,
                    tier=tier,
                    instrument_class=instrument_class,
                    pass1_result=pass1_result,
                    content_by_qt=content_by_qt,
                )
                work_items.append({
                    "cell_id": cell_id,
                    "group_id": group_id,
                    "params_path": params_path,
                    "prompt": prompt,
                })

    if not work_items:
        logger.info("No cells need Pass 2 processing — all done or no pass1 results found")
        state["pass2_complete"] = True
        save_state(state)
        return

    logger.info("Running Pass 2 batch for %d cells", len(work_items))
    prompts = [item["prompt"] for item in work_items]
    results = chain.batch(
        [[HumanMessage(content=p)] for p in prompts],
        config={"max_concurrency": 50},
        return_exceptions=True,
    )

    # Save results
    for item, result in zip(work_items, results):
        cell_id = item["cell_id"]
        group_id = item["group_id"]
        params_path = item["params_path"]

        if isinstance(result, Exception):
            logger.error("Pass 2 LLM call failed for cell %s: %s", cell_id, result)
            continue

        pass2_result: Pass2Result = result
        save_json(params_path, pass2_result.model_dump())
        logger.info("[PASS2_SAVED] %s (%d values)", cell_id, len(pass2_result.parameter_values))

        # Log parameters where all lifecycle values are not_found
        for pv in pass2_result.parameter_values:
            if (
                pv.admission_value == "not_found"
                and pv.continuing_value == "not_found"
                and pv.removal_value == "not_found"
            ):
                logger.info(
                    "[VALUE_NOT_FOUND] cell %s | group %s | param %s — all lifecycle values not found",
                    cell_id, group_id, pv.parameter_id,
                )

    state["pass2_complete"] = True
    save_state(state)
    logger.info("Phase 2 Pass 2 complete")


# ---------------------------------------------------------------------------
# Run all steps sequentially (original)
# ---------------------------------------------------------------------------

def run_all(state: dict) -> None:
    """Run all Phase 2 steps: form_groups → run_pass1 → run_pass2."""
    logger.info("========== Phase 2 Start ==========")

    logger.info("--- Step 1: Form groups ---")
    form_groups(state)

    logger.info("--- Step 2: Pass 1 (parameter structure) ---")
    run_pass1(state)

    logger.info("--- Step 3: Pass 2 (parameter values) ---")
    run_pass2(state)

    logger.info("========== Phase 2 Complete ==========")


# ===========================================================================
# PARAMETER DICTIONARY (for 3P-classify system prompt)
# ===========================================================================

PARAMETER_DICTIONARY_TEXT = """
## Parameter Dictionary v1

### Part I. Core Dictionary

#### Equities (В02.1)

Quantitative instrument requirements:
- П01: Free float / Public float / Shares in public hands — Almost universal
- П02: Minimum market capitalization — Very frequent
- П03: Minimum number of shareholders / holders — Very frequent
- П04: Minimum share price / Bid price — Frequent (especially US)
- П05: Minimum shares outstanding — Medium
- П06: Minimum trading volume — Rare at admission, more common for continuing
- П33: Minimum public allocation at IPO — Medium (HK GEM: 5%)
  NOTE on П33: Differs from П01 (free float). Free float = result requirement (shares in circulation). П33 = placement structure requirement (fraction to be allocated to public tranche at IPO). Can coexist with П01.

Quantitative issuer requirements:
- П07: Track record / Operating history — Very frequent
- П08: Profit / Earnings test — Frequent
- П09: Net tangible assets / Shareholders' equity — Frequent
  NOTE on П09: For investing companies on MTF may be expressed as minimum raised at admission (e.g. AIM: £6M). Record via question 4 (varies by issuer type).
- П10: Revenue requirement — Medium
- П11: Working capital requirement — Medium
  NOTE on П11: In some jurisdictions (HK) requires formal working capital sufficiency statement from issuer and sponsor for 12 months.

Qualitative requirements:
- П12: Corporate governance standards — Very frequent
  NOTE on П12: Includes board composition, committee requirements, and in some jurisdictions physical presence of management (HK: 2 executive directors — HK residents; HK GEM: 2 authorized representatives + qualified secretary).
- П13: Auditor / Accounting standards — Very frequent

Infrastructure requirements:
- П14: Sponsor / Nomad / Listing agent — Frequent
- П15: Market maker / Liquidity provider — Medium
- П16: Prospectus / Admission document — Almost universal

Restrictive mechanisms:
- П17: Lock-up / Lock-in period — Frequent
- П18: Escrow restrictions — Rare

Removal phase parameters:
- П34: Maximum suspension period before compulsory delisting — Frequent (HK MB: 18 months, GEM: 12 months)
  NOTE on П34: Quantitative parameter for phase G07.3→G07.4. Defines after what period of continuous suspension the venue initiates compulsory delisting. Some jurisdictions fixed (HK), some discretionary (UK: "6 months — special circumstances").

Base eligibility preconditions:
- П31: Eligibility preconditions — Almost universal
  COMPOSITION: Binary (yes/no) preconditions checked at admission:
  - Free transferability of securities
  - Fully paid, free of liens
  - Settlement eligibility (CREST, CCASS, Euroclear, etc.)
  - Whole-class application
  Specific infrastructure (CREST vs. CCASS) differs by jurisdiction, but the set of conditions is near-universal.

#### Bonds / Debt instruments (В02.2)

Quantitative instrument requirements:
- П19: Minimum issue size / Minimum denomination — Very frequent
- П20: Minimum denomination / Minimum lot size — Very frequent
- П21: Credit rating requirement — Medium
- П22: Minimum maturity / Remaining term — Medium

Quantitative issuer requirements:
- П07: Track record — Frequent
- П09: Net assets / Equity — Medium
- П35: Guarantor eligibility — Frequent for guaranteed issues
  NOTE on П35: Applies to guaranteed issues. Guarantor must meet same or comparable track record and equity requirements as issuer (HK: ≥HK$100M guarantor equity). If no guarantee: not_applicable.

Qualitative requirements:
- П13: Accounting standards / Auditor — Very frequent
- П23: Trustee / Fiscal agent / Paying agent — Frequent
- П32: Investor eligibility restriction — Frequent
  NOTE on П32: Defines whether instrument is open to all investors (retail) or only professional/qualified (professional investors only). Affects prospectus, disclosure, minimum denomination requirements.

Infrastructure:
- П16: Prospectus / Listing particulars — Almost universal
- П14: Sponsor / Listing agent — Medium
- П31: Eligibility preconditions — Almost universal

Removal phase:
- П03: Minimum number of holders (for bonds: qualitative test) — Medium
  NOTE on П03 for bonds: In some jurisdictions (UK ATT) applied as qualitative test without numeric threshold: "sufficient number of registered holders to ensure orderly market."

#### Funds (В02.3)

Quantitative instrument requirements:
- П01: Free float / Public spread / Units in public hands — Frequent
- П03: Minimum number of unitholders — Frequent
- П24: Minimum NAV / Minimum fund size / Minimum AUM — Very frequent
- П25: Diversification requirements — Frequent
- П32: Investor eligibility restriction — Frequent

Fund manager requirements:
- П26: Fund manager authorization / licensing — Very frequent
- П27: Custodian / Depositary requirements — Very frequent
- П07: Track record of fund / manager — Medium
- П36: Product-level regulatory authorisation — Very frequent
  NOTE on П36: Differs from П26 (manager-level licensing). П26 = authorization of operator. П36 = authorization of fund as investment product. Example: HK — SFC authorisation of CIS is mandatory and must be maintained; revocation = delisting basis.

Infrastructure:
- П14: Sponsor / Listing agent — Medium
- П16: Prospectus / Key investor document — Almost universal
- П15: Market maker / Authorized participant (for ETF) — Frequent for ETF
- П31: Eligibility preconditions — Almost universal

#### Depositary Receipts (В02.4)

Quantitative requirements:
- П01: Free float / Public float of DRs — Frequent
- П02: Minimum market capitalization of DRs / Underlying — Frequent
- П03: Minimum number of DR holders — Medium

Underlying instrument requirements:
- П28: Primary listing requirement for underlying security — Very frequent
- П29: Recognized jurisdiction / Equivalence — Frequent
- П07: Track record (via DR regime) — Frequent
- П08: Profit test (via DR regime) — Frequent
- П09: Net assets test (via DR regime) — Frequent
- П10: Revenue test (via DR regime) — Medium
- П11: Working capital sufficiency (via DR regime) — Medium
  NOTE on П07–П11 for DR: In some jurisdictions (HK) the same financial tests as for equity (three alternative tests Rule 8.05) apply to DR issuer. These are not separate parameters — they are equity tests applied via DR regime.

Infrastructure:
- П30: Depositary bank requirements — Very frequent
- П16: Prospectus — Almost universal
- П31: Eligibility preconditions — Almost universal

### Part II. Distinct Regime Prerequisites

Activated only for cells with distinct_regime=true (secondary listing with principally different requirements structure).

- П-D01: Qualifying home listing — Universal for distinct
  Issuer must have primary listing on a recognized venue. List of recognized venues is jurisdiction-specific.
- П-D02: Central management and control location — Frequent (UK)
  Management centre in country of incorporation or country of home listing.
- П-D03: Home listing status dependency — Universal for distinct
  Obligation to notify of suspension/withdrawal of home listing; may be basis for suspension/delisting on secondary venue.
- П-D04: Automatic waivers package — Frequent (HK)
  Set of exceptions from standard rules for secondary issuers (specific rulebook chapters).
- П-D05: Migration triggers — Medium (HK)
  Conditions under which secondary issuer is treated as primary (HK example: ≥55% trading on HK → waiver cancellation).

### Part III. Deferred Elements Registry

Elements not in the parameter dictionary but requiring accounting in other research components:

III-A. Procedural requirements (Д02): Operational admission conditions (timelines, notification procedures, application formats). Not threshold values for comparative analysis.
III-B. Continuing obligations (Д03/Д05): Post-admission issuer duties: disclosure, periodic reporting, major shareholding notifications.
III-C. Sub-class modifiers (Г08): Specific rules for instrument sub-classes that modify standard admission regime. Not separate parameters — context in which standard parameters take different values.
III-D. DR structural restrictions: DR-specific rules with nature of structural prohibitions, not threshold values.
"""


PARAM_NAMES_RU: dict[str, str] = {
    "П01": "Free float",
    "П02": "Минимальная рыночная капитализация",
    "П03": "Минимальное число акционеров / держателей",
    "П04": "Минимальная цена акции",
    "П05": "Минимальный объём выпуска",
    "П06": "Минимальный объём торгов",
    "П07": "Финансовая история / операционный трек-рекорд",
    "П08": "Требования к прибыли",
    "П09": "Требования к активам / собственному капиталу",
    "П10": "Требования к выручке",
    "П11": "Требования к рабочему капиталу",
    "П12": "Корпоративное управление",
    "П13": "Аудитор и стандарты отчётности",
    "П14": "Спонсор / номад / листинговый агент",
    "П15": "Маркет-мейкер / поставщик ликвидности",
    "П16": "Проспект / информационный документ",
    "П17": "Локап",
    "П18": "Эскроу-ограничения",
    "П19": "Минимальный объём выпуска (облигации)",
    "П20": "Минимальный номинал",
    "П21": "Требования к кредитному рейтингу",
    "П22": "Минимальный срок до погашения",
    "П23": "Доверительный управляющий / фискальный агент",
    "П24": "Минимальный NAV / размер фонда",
    "П25": "Требования к диверсификации",
    "П26": "Авторизация / лицензирование управляющего",
    "П27": "Требования к кастодиану / депозитарию",
    "П28": "Требование к первичному листингу базового актива",
    "П29": "Признанная юрисдикция / эквивалентность",
    "П30": "Требования к банку-депозитарию (DR)",
    "П31": "Базовые условия допускаемости",
    "П32": "Ограничения допуска инвесторов",
    "П33": "Минимальная доля публичного размещения при IPO",
    "П34": "Максимальный срок приостановки до принудительного исключения",
    "П35": "Допускаемость гаранта",
    "П36": "Регуляторная авторизация продукта",
    "П-D01": "Квалифицирующий первичный листинг (для вторичного листинга)",
    "П-D02": "Место центрального управления",
    "П-D03": "Зависимость от статуса первичного листинга",
    "П-D04": "Пакет автоматических исключений (waiver package)",
    "П-D05": "Триггеры миграции в первичный режим",
}


def _build_translate_prompt(pass2_data: dict) -> str:
    """Build user prompt for Pass 2 translation to Russian."""
    return f"""Translate the following parameter value data from English to Russian.

RULES:
- Translate ONLY these text fields: value, calculation_methodology, alternatives, variations, note
- Do NOT translate: source, parameter_id, parameter_name, lifecycle_phase, status, linkages
- Preserve all technical terms, rule numbers, and legal references in their original language
  (e.g. "UKLR 6.14.3R", "Chapter 8", "Rule 8.08", "HK$", "£" — keep as-is)
- Keep the JSON structure identical — return the same structure with translated text fields
- Return valid JSON only — no markdown, no commentary outside the JSON

Input data:
{json.dumps(pass2_data, ensure_ascii=False, indent=2)}
"""


# ===========================================================================
# 3P-classify helpers
# ===========================================================================

def _params_as_text(parameters: list[dict]) -> str:
    """Convert pass1.json parameters list to readable text for prompts."""
    lines = []
    for p in parameters:
        pid = p.get("parameter_id", "")
        pname = p.get("parameter_name", "")
        status = p.get("status", "")
        desc = p.get("description", "")
        note = p.get("note", "")
        if status in ("not_applicable", "data_not_found", "not_found"):
            lines.append(f"{pid} ({pname}) [{status}]:")
            if note:
                lines.append(f"  {note}")
            elif desc:
                lines.append(f"  {desc[:200]}")
            else:
                lines.append(f"  No data.")
        else:
            lines.append(f"{pid} ({pname}) [{status}]:")
            lines.append(f"  {desc}")
        lines.append("")
    return "\n".join(lines)


def _build_3p_classify_system_prompt() -> str:
    """Build the system prompt for 3P-classify (includes full dictionary + rules)."""
    return f"""You are an expert analyst in securities listing regulations. Your task is to:
1. Classify UNKNOWN (additional) parameters found in Pass 1 into categories A, B, or C.
2. Evaluate which parameters need 3P drill-down research.
3. Generate 3P drill-down prompts for parameters that need further research.
4. Generate a dynamic JSON schema for 3P results.

{PARAMETER_DICTIONARY_TEXT}

---

## CLASSIFICATION RULES FOR UNKNOWN PARAMETERS

When you encounter a parameter in "additional_parameters" not in the dictionary:

CATEGORY A — "Maps to existing": the parameter is a reformulation or sub-aspect of an existing dictionary parameter.
→ Assign the existing parameter ID. Explain the mapping.

CATEGORY B — "Candidate for new": a genuinely new parameter, not covered by П01–П36.
→ Assign temporary ID (CANDIDATE_01, CANDIDATE_02, ...).
  Provide: name, description, in which lifecycle phases found, in how many groups encountered.
→ Include in 3P prompts as CANDIDATE_XX (do not lose the data).

CATEGORY C — "Not a parameter": a procedural, architectural, or institutional element mistakenly extracted as a parameter.
Example: "two-gate admission model" = architectural element. "FCA supervisory powers" = institutional context.
→ Exclude from further processing. Log with reason.

---

## DRILL-DOWN CRITERIA

A parameter needs a 3P drill-down query if the Pass 1 description contains ANY of:
1. Reference to an external document without disclosing its content
   Example: "calculated per DDES methodology", "as defined in SFO Schedule 1"
2. Ambiguity in exclusions
   Example: "holdings above certain thresholds are excluded" — which thresholds exactly?
3. Mention of multiple alternative methodologies without detail
   Example: "may use either the profit test or the market cap test" — what are the specific conditions of each?

A parameter does NOT need drill-down if:
- It is binary (yes/no, exists/not exists) — nothing to clarify
- The Pass 1 description already contains exact thresholds, calculation methodology, exclusions, and verification mechanism
- It was marked "not_found" or "not_applicable" in Pass 1

---

## KNOWN PARAMETER LINKAGES

When drilling down on one parameter in a linkage, ALWAYS ask about interaction with the other:
- П04 (min share price) × П05 (min number of shares) = implicit monetary threshold
- П20 (min denomination, bonds) → П32 (investor eligibility): high denomination = de facto professional only
- П01 (free float %) ↔ П03 (min market cap of free float): percentage and absolute value as alternatives
- П15 (market maker) → П04 (min shareholders): market maker presence may lower shareholder count threshold
- П08 (profit test) ↔ П09 (assets/equity test) ↔ П10 (revenue test): alternative eligibility paths — clarify conditions for each

---

## TEMPLATE FOR 3P DRILL-DOWN QUERY

Parameter: [ID and name]
Venue: [venue name]
Jurisdiction: [jurisdiction]
Instrument class: [class]

What is already known from the overview research:
[paste Pass 1 description for this parameter]

What needs clarification:
[specific question — generated by LLM based on drill-down criteria]

If this parameter is part of a linkage with [linked parameter]:
Does the calculation of [this parameter] depend on or interact with [linked parameter]? How?

Preferred source type: exchange rulebook, regulator guidance, or official methodology document. Do NOT use secondary analytical sources.
Cite specific rule numbers for each finding.

---

## OUTPUT FORMAT

Return your response as valid JSON with this exact structure:
{{
  "group_id": "string",
  "unknown_classifications": [
    {{
      "original_id": "ADDITIONAL_1",
      "original_name": "string",
      "category": "A",
      "reason": "string",
      "mapped_to_id": "string or null",
      "candidate_id": "string or null",
      "lifecycle_phases": "string or null"
    }}
  ],
  "drill_down_evaluations": [
    {{
      "parameter_id": "П01 or CANDIDATE_01",
      "parameter_name": "string",
      "needs_drill_down": true,
      "reason": "string",
      "prompt": "string or null"
    }}
  ],
  "three_p_required": true,
  "three_p_combined_prompt": "string or null",
  "three_p_schema": {{
    "parameters": [
      {{
        "parameter_id": "string",
        "parameter_name": "string",
        "lifecycle_phases": "string",
        "definition_and_value": {{"description": "string", "source": "string"}},
        "calculation_methodology": {{"description": "string", "source": "string"}},
        "exclusions_and_inclusions": {{"description": "string", "source": "string"}},
        "alternatives": {{"description": "string", "source": "string"}},
        "variations": {{"description": "string", "source": "string"}},
        "linked_requirements": {{"description": "string", "source": "string"}},
        "differences_across_phases": {{"description": "string", "source": "string"}}
      }}
    ]
  }}
}}

IMPORTANT: three_p_schema must be null if three_p_required is false.
IMPORTANT: Return ONLY valid JSON — no markdown, no explanations outside the JSON.
"""


def _build_3p_classify_user_prompt(
    group_id: str,
    instrument_class: str,
    name_ru: str,
    market_type: str,
    admission_path_type: str,
    pass1_parameters: list[dict],
    additional_parameters: list[dict],
) -> str:
    """Build the user prompt for 3P-classify."""
    # Determine jurisdiction name (English) for the prompt
    jur_config = JURISDICTION_BY_RU.get(name_ru, {})
    jurisdiction = jur_config.get("name_en", name_ru)

    params_text = _params_as_text(pass1_parameters)
    add_params_text = _params_as_text(additional_parameters) if additional_parameters else "(none)"

    return f"""Here is the Pass 1 result for group: {group_id}
Instrument class: {instrument_class}
Jurisdiction: {jurisdiction}
Market type: {market_type}
Admission path type: {admission_path_type}

--- PASS 1 PARAMETERS ---
{params_text}

--- ADDITIONAL PARAMETERS (not in checklist) ---
{add_params_text}

Step 1: Classify each ADDITIONAL parameter per the rules in system prompt (Category A / B / C).
For Category A: assign the existing dictionary parameter ID.
For Category B: assign CANDIDATE_XX ID.
For Category C: exclude and log with reason.

Step 2: For each parameter in PASS 1 PARAMETERS with status "applicable" or "found" and each CANDIDATE_XX parameter:
- Evaluate: does it need 3P drill-down? Apply criteria from system prompt.
- If yes: generate a Parallel API prompt using the template from system prompt.

Step 3: Generate a dynamic JSON schema for 3P results for this group (only parameters needing drill-down).

Return your response as valid JSON with the structure specified in the system prompt.
Set group_id="{group_id}" in your response.
"""



# ===========================================================================
# Step: 3P-classify — classify UNKNOWN params + generate 3P prompts
# ===========================================================================

def run_3p_classify(groups: dict, data_root: Path, llm: ChatOpenAI) -> None:
    """
    For each group: load pass1.json → build LLM prompt → classify UNKNOWN parameters
    (A/B/C) + evaluate necessity of drill-down + generate 3P prompts → save results.

    Saves per group:
        group_dir/pass1_unknowns.json  — classifications + drill-down evaluations
        group_dir/3P_prompt.txt        — combined prompt (only if three_p_required)
        group_dir/3P_schema.json       — dynamic schema (only if three_p_required)

    Idempotency: skip group if pass1_unknowns.json already exists.
    """
    logger.info("Starting 3P-classify (UNKNOWN parameter classification + 3P prompt generation)")

    system_prompt = _build_3p_classify_system_prompt()

    # Collect work items
    work_items: list[dict] = []

    seen_name_ru: set[str] = set()
    for venue in PILOT_VENUES:
        name_ru = venue["name_ru"]
        if name_ru in seen_name_ru:
            continue
        seen_name_ru.add(name_ru)
        groups_base = COUNTRIES_DIR / name_ru / "level_3" / "_groups"
        if not groups_base.exists():
            continue

        for group_dir in sorted(groups_base.iterdir()):
            if not group_dir.is_dir():
                continue
            group_id = group_dir.name

            unknowns_path = group_dir / "pass1_unknowns.json"
            if unknowns_path.exists():
                logger.info("[SKIP] pass1_unknowns.json already exists for group %s", group_id)
                continue

            pass1_path = group_dir / "pass1.json"
            if not pass1_path.exists():
                logger.info("[SKIP] No pass1.json for group %s — cannot run 3P-classify", group_id)
                continue

            pass1_data = load_json(pass1_path)
            if not pass1_data:
                logger.warning("pass1.json empty for group %s — skipping", group_id)
                continue

            meta_path = group_dir / "group_meta.json"
            group_meta = load_json(meta_path)
            if not group_meta:
                logger.warning("group_meta.json missing for group %s — skipping", group_id)
                continue

            user_prompt = _build_3p_classify_user_prompt(
                group_id=group_id,
                instrument_class=pass1_data.get("instrument_class", ""),
                name_ru=group_meta.get("name_ru", name_ru),
                market_type=group_meta.get("market_type", ""),
                admission_path_type=group_meta.get("admission_path_type", ""),
                pass1_parameters=pass1_data.get("parameters", []),
                additional_parameters=pass1_data.get("additional_parameters", []),
            )

            work_items.append({
                "group_id": group_id,
                "group_dir": group_dir,
                "unknowns_path": unknowns_path,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            })

    if not work_items:
        logger.info("No groups need 3P-classify — all done or no pass1 results found")
        return

    logger.info("Running 3P-classify batch for %d groups", len(work_items))

    # Build message lists: [SystemMessage, HumanMessage] for each group
    messages_list = [
        [
            SystemMessage(content=item["system_prompt"]),
            HumanMessage(content=item["user_prompt"]),
        ]
        for item in work_items
    ]

    chain = llm.with_structured_output(ThreePClassifyResult)
    results = chain.batch(
        messages_list,
        config={"max_concurrency": 50},
        return_exceptions=True,
    )

    completed = 0
    skipped = 0
    failed = 0

    for item, result in zip(work_items, results):
        group_id = item["group_id"]
        group_dir: Path = item["group_dir"]
        unknowns_path: Path = item["unknowns_path"]

        if isinstance(result, Exception):
            logger.error("[ERROR] 3P-classify LLM call failed for group %s: %s", group_id, result)
            failed += 1
            continue

        # result is ThreePClassifyResult — already parsed by with_structured_output
        parsed: ThreePClassifyResult = result

        # Save pass1_unknowns.json
        save_json(unknowns_path, parsed.model_dump())
        logger.info(
            "[3P_CLASSIFY_SAVED] %s — %d classifications, %d evaluations, three_p_required=%s",
            group_id,
            len(parsed.unknown_classifications),
            len(parsed.drill_down_evaluations),
            parsed.three_p_required,
        )

        # Save 3P_prompt.txt and 3P_schema.json only if three_p_required
        if parsed.three_p_required:
            combined_prompt = parsed.three_p_combined_prompt
            three_p_schema = parsed.three_p_schema.model_dump() if parsed.three_p_schema else None

            if combined_prompt:
                prompt_path = group_dir / "3P_prompt.txt"
                with open(prompt_path, "w", encoding="utf-8") as f:
                    f.write(combined_prompt)
                logger.info("[3P_PROMPT_SAVED] %s", group_id)

            if three_p_schema:
                schema_path = group_dir / "3P_schema.json"
                save_json(schema_path, three_p_schema)
                logger.info("[3P_SCHEMA_SAVED] %s", group_id)

        completed += 1

    logger.info(
        "3P-classify complete: %d completed, %d skipped, %d failed",
        completed, skipped, failed,
    )


# ===========================================================================
# Step: 3P-execute — run 3P drill-down via Parallel API
# ===========================================================================

# Formal JSON Schema for 3P Parallel API output.
# The prompt specifies WHICH parameters to research; this schema defines HOW to structure the output.
_THREE_P_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "parameters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "parameter_id": {"type": "string"},
                    "parameter_name": {"type": "string"},
                    "lifecycle_phases": {"type": "string"},
                    "definition_and_value": {
                        "type": "object",
                        "properties": {"description": {"type": "string"}, "source": {"type": "string"}},
                        "required": ["description", "source"],
                    },
                    "calculation_methodology": {
                        "type": "object",
                        "properties": {"description": {"type": "string"}, "source": {"type": "string"}},
                        "required": ["description", "source"],
                    },
                    "exclusions_and_inclusions": {
                        "type": "object",
                        "properties": {"description": {"type": "string"}, "source": {"type": "string"}},
                        "required": ["description", "source"],
                    },
                    "alternatives": {
                        "type": "object",
                        "properties": {"description": {"type": "string"}, "source": {"type": "string"}},
                        "required": ["description", "source"],
                    },
                    "variations": {
                        "type": "object",
                        "properties": {"description": {"type": "string"}, "source": {"type": "string"}},
                        "required": ["description", "source"],
                    },
                    "linked_requirements": {
                        "type": "object",
                        "properties": {"description": {"type": "string"}, "source": {"type": "string"}},
                        "required": ["description", "source"],
                    },
                    "differences_across_phases": {
                        "type": "object",
                        "properties": {"description": {"type": "string"}, "source": {"type": "string"}},
                        "required": ["description", "source"],
                    },
                },
                "required": ["parameter_id", "parameter_name", "lifecycle_phases"],
            },
        }
    },
    "required": ["parameters"],
}


def run_3p_execute(groups: dict, data_root: Path) -> None:
    """
    For each group with a 3P_prompt.txt:
    - Load prompt
    - Run via Parallel API (processor=core, JSON output with fixed schema)
    - Save result as group_dir/3P_raw.json

    Uses a fixed formal JSON Schema (_THREE_P_OUTPUT_SCHEMA) — the 3P_schema.json file
    is kept as documentation of which parameters were identified for drill-down.

    Idempotency: skip if 3P_raw.json already exists.
    All tasks are launched first, then polled concurrently via poll_all.
    """
    from pipeline.parallel_runner import launch_task, poll_all, load_state as pr_load_state
    from pipeline.config import LOGS_DIR

    logger.info("Starting 3P-execute (Parallel API drill-down research)")

    three_p_state_file = LOGS_DIR / "phase2_3p_state.json"
    state = pr_load_state(three_p_state_file)

    skipped = 0
    tasks_to_poll: list[tuple[str, Any]] = []

    # Pass 1: launch all tasks (idempotent — already-launched groups are skipped by launch_task)
    seen_name_ru: set[str] = set()
    for venue in PILOT_VENUES:
        name_ru = venue["name_ru"]
        if name_ru in seen_name_ru:
            continue
        seen_name_ru.add(name_ru)
        groups_base = COUNTRIES_DIR / name_ru / "level_3" / "_groups"
        if not groups_base.exists():
            continue

        for group_dir in sorted(groups_base.iterdir()):
            if not group_dir.is_dir():
                continue
            group_id = group_dir.name
            raw_path = group_dir / "3P_raw.json"

            if raw_path.exists():
                logger.info("[SKIP] 3P_raw.json already exists for group %s", group_id)
                skipped += 1
                continue

            prompt_path = group_dir / "3P_prompt.txt"
            if not prompt_path.exists():
                logger.info("[SKIP] No 3P_prompt.txt for group %s — skipping", group_id)
                skipped += 1
                continue

            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_text = f.read()

            task_key = f"3p_{group_id}"
            try:
                launch_task(
                    task_key=task_key,
                    prompt=prompt_text,
                    output_schema=_THREE_P_OUTPUT_SCHEMA,
                    state=state,
                    processor="core",
                    state_file=three_p_state_file,
                )
            except Exception as exc:
                logger.error("[ERROR] Failed to launch 3P task for group %s: %s", group_id, exc)
                continue

            # save_fn: content is a dict (JSON schema output from Parallel API)
            def _make_save_fn(save_path: Path):
                def save_fn(content: dict) -> Path:
                    save_json(save_path, content)
                    return save_path
                return save_fn

            tasks_to_poll.append((task_key, _make_save_fn(raw_path)))

    if not tasks_to_poll:
        logger.info("No 3P tasks to poll (all skipped or already done)")
        logger.info("3P-execute complete: 0 completed, %d skipped, 0 failed", skipped)
        return

    logger.info("Launched %d tasks — polling all concurrently", len(tasks_to_poll))

    # Pass 2: poll all tasks concurrently (round-robin until all complete)
    poll_results = poll_all(tasks_to_poll, state, three_p_state_file)

    completed = sum(1 for v in poll_results.values() if v is not None)
    failed = len(poll_results) - completed

    # Log per-group outcome
    for task_key, content in poll_results.items():
        group_id = task_key.removeprefix("3p_")
        if content is not None:
            logger.info("[3P_EXECUTE_SAVED] %s", group_id)
        else:
            entry = state["tasks"].get(task_key, {})
            if entry.get("status") == "done":
                logger.info("[3P_EXECUTE_ALREADY_DONE] %s", group_id)
                completed += 1
                failed -= 1
            else:
                logger.error("[ERROR] 3P-execute failed for group %s", group_id)

    logger.info(
        "3P-execute complete: %d completed, %d skipped, %d failed",
        completed, skipped, failed,
    )


# ===========================================================================
# New Pass 2 — extract parameter values per cell using Pass 1 + 3P results
# ===========================================================================

def _build_new_pass2_system_prompt() -> str:
    """System prompt for new Pass 2 (parameter value extraction per cell)."""
    return """You are an expert analyst in securities listing regulations.
Your task is to extract specific parameter VALUES for a given venue/tier/instrument_class cell.

You will be given:
1. The parameter framework for the group (from Pass 1) — common structure across venues
2. 3P drill-down results (if available) — targeted research on specific parameters
3. Cell-specific research data (3A/3B/3C query types that are GREEN or YELLOW)

Your job is to extract the SPECIFIC VALUE for each applicable parameter FOR THIS SPECIFIC CELL.

Rules:
- Report the specific numeric value or qualitative criterion for THIS venue/tier
- If a value differs by lifecycle phase (admission / continuing / suspension / delisting) — report each phase separately
- If the 3P results provide additional detail on calculation methodology — incorporate it
- If no data found for this cell — mark as "not_found" with reason
- If parameter does not apply to this cell — mark as "not_applicable" with reason
- RED lifecycle phases (no data): explicitly note them as not covered
- Do NOT re-describe parameter structure — only report values specific to this cell

Return a JSON array (not wrapped in an object) of parameter values.
IMPORTANT: Return ONLY a valid JSON array — no markdown, no explanations outside the JSON.
"""


def _build_new_pass2_user_prompt(
    cell_id: str,
    venue_key: str,
    tier: str,
    instrument_class: str,
    group_id: str,
    name_ru: str,
    pass1_data: dict,
    three_p_raw: Optional[dict],
    content_by_qt: dict,
    red_qts: list[str],
) -> str:
    """Build user prompt for new Pass 2 (per cell)."""
    jur_config = JURISDICTION_BY_RU.get(name_ru, {})
    jurisdiction = jur_config.get("name_en", name_ru)

    # Format Pass 1 parameters as readable text
    pass1_params_text = _params_as_text(pass1_data.get("parameters", []))

    # Also include applicable additional parameters classified as A or B
    add_params = pass1_data.get("additional_parameters", [])
    if add_params:
        pass1_params_text += "\n--- ADDITIONAL PARAMETERS ---\n"
        pass1_params_text += _params_as_text(add_params)

    # Format 3P results
    if three_p_raw:
        three_p_text = json.dumps(three_p_raw, ensure_ascii=False, indent=2)
    else:
        three_p_text = "Not available"

    # Format cell research data
    cell_data_parts = []
    for qt, content in content_by_qt.items():
        cell_data_parts.append(_serialize_cell_data(cell_id, qt, content))
    cell_data_text = "\n\n".join(cell_data_parts) if cell_data_parts else "(no cell data available)"

    covered_phases = list(content_by_qt.keys())
    not_covered = red_qts

    return f"""You are given:
1. Parameter framework for group [{group_id}] — extracted in Pass 1
2. Drill-down results from targeted research (3P) — {"available" if three_p_raw else "NOT available"}
3. Overview research data (3A+3B+3C) for a specific cell: {venue_key} / {tier} / {instrument_class}

Jurisdiction: {jurisdiction}

--- PARAMETER FRAMEWORK (Pass 1) ---
{pass1_params_text}

--- 3P DRILL-DOWN RESULTS ---
{three_p_text}

--- CELL RESEARCH DATA ---
{cell_data_text}

Lifecycle phases covered (GREEN/YELLOW data): {covered_phases}
Lifecycle phases NOT covered (RED in validation): {not_covered}

For each parameter in the framework with status "applicable" or "found":
- Extract the SPECIFIC VALUE for this cell (venue: {venue_key} / tier: {tier} / instrument_class: {instrument_class})
- If 3P provided additional detail on calculation methodology — incorporate it
- If no data found for this cell — mark as "not_found" with reason
- If not applicable to this cell — mark as "not_applicable" with reason
- Note the lifecycle phase (admission / continuing / suspension / delisting)

Return a JSON array of parameter values:
[
  {{
    "parameter_id": "П01",
    "parameter_name": "string",
    "lifecycle_phase": "admission | continuing | suspension | delisting | multiple",
    "value": "specific threshold or criterion for this cell",
    "calculation_methodology": "string or null",
    "alternatives": "string or null",
    "variations": "string or null",
    "linkages": ["П02", "П03"],
    "source": "specific rule/chapter",
    "drill_down_applied": true,
    "status": "found | not_found | not_applicable",
    "note": "string"
  }}
]

Set cell_id="{cell_id}" context — this is the cell you are analyzing.
IMPORTANT: Return ONLY a valid JSON array — no markdown, no explanations outside the JSON.
"""


def run_new_pass2(state: dict, llm: ChatOpenAI) -> None:
    """
    For each GREEN/YELLOW cell: load Pass 1 framework + 3P results (if any) +
    cell research data, build prompt, run LLM batch to extract specific parameter values.

    Saves per cell: cell_dir/pass2.json

    Idempotency: skip if pass2.json already exists.
    RED cells are skipped entirely.
    """
    logger.info("Starting new Pass 2 (parameter value extraction per cell with 3P integration)")

    work_items: list[dict] = []

    seen_name_ru: set[str] = set()
    for venue in PILOT_VENUES:
        name_ru = venue["name_ru"]
        if name_ru in seen_name_ru:
            continue
        seen_name_ru.add(name_ru)
        groups_base = COUNTRIES_DIR / name_ru / "level_3" / "_groups"
        if not groups_base.exists():
            continue

        for group_dir in sorted(groups_base.iterdir()):
            if not group_dir.is_dir():
                continue
            group_id = group_dir.name

            pass1_path = group_dir / "pass1.json"
            if not pass1_path.exists():
                logger.info("[SKIP] No pass1.json for group %s — skipping new Pass 2", group_id)
                continue

            pass1_data = load_json(pass1_path)
            if not pass1_data:
                logger.warning("pass1.json empty for group %s — skipping", group_id)
                continue

            meta_path = group_dir / "group_meta.json"
            group_meta = load_json(meta_path)
            if not group_meta:
                logger.warning("group_meta.json missing for group %s — skipping", group_id)
                continue

            gname_ru: str = group_meta.get("name_ru", name_ru)
            instrument_class: str = group_meta.get("instrument_class", "")

            # Load 3P results if available
            three_p_raw_path = group_dir / "3P_raw.json"
            three_p_raw: Optional[dict] = load_json(three_p_raw_path) if three_p_raw_path.exists() else None

            for cell_info in group_meta.get("cells", []):
                cell_id: str = cell_info["cell_id"]
                venue_key: str = cell_info["venue_key"]
                tier: str = cell_info["tier"]
                valid_qts: list[str] = cell_info.get("valid_qts", [])
                excluded_qts: list[str] = cell_info.get("excluded_qts", [])

                cell_dir = get_country_level3_dir(gname_ru, venue_key) / cell_id
                pass2_path = cell_dir / "pass2.json"

                if pass2_path.exists():
                    logger.info("[SKIP] pass2.json already exists for cell %s", cell_id)
                    continue

                if not valid_qts:
                    logger.info("[SKIP] No valid query types for cell %s (all RED)", cell_id)
                    continue

                # Load cell content for valid (GREEN/YELLOW) query types
                content_by_qt: dict[str, Any] = {}
                for qt in valid_qts:
                    # Use _cell.json if exists, otherwise fall back to _raw.json content
                    cell_json_path = cell_dir / f"{qt}_cell.json"
                    raw_path = cell_dir / f"{qt}_raw.json"

                    if cell_json_path.exists():
                        cell_data = load_json(cell_json_path)
                        if cell_data:
                            content_by_qt[qt] = cell_data
                            continue

                    if raw_path.exists():
                        raw_data = load_json(raw_path)
                        if raw_data:
                            content_by_qt[qt] = raw_data.get("content", raw_data)
                    else:
                        logger.warning(
                            "No data file for cell %s / qt %s — skipping this qt",
                            cell_id, qt,
                        )

                if not content_by_qt:
                    logger.warning("[CELL_SKIPPED] %s — no data available for new Pass 2", cell_id)
                    continue

                # Determine RED query types (not covered)
                red_qts = excluded_qts[:]
                # Also add valid_qts for which we couldn't load data
                for qt in valid_qts:
                    if qt not in content_by_qt:
                        red_qts.append(qt)

                prompt = _build_new_pass2_user_prompt(
                    cell_id=cell_id,
                    venue_key=venue_key,
                    tier=tier,
                    instrument_class=instrument_class,
                    group_id=group_id,
                    name_ru=gname_ru,
                    pass1_data=pass1_data,
                    three_p_raw=three_p_raw,
                    content_by_qt=content_by_qt,
                    red_qts=red_qts,
                )

                work_items.append({
                    "cell_id": cell_id,
                    "group_id": group_id,
                    "pass2_path": pass2_path,
                    "prompt": prompt,
                })

    if not work_items:
        logger.info("No cells need new Pass 2 processing — all done or no pass1 results found")
        return

    logger.info("Running new Pass 2 batch for %d cells", len(work_items))

    system_prompt = _build_new_pass2_system_prompt()
    chain = _get_llm().with_structured_output(Pass2CellResult)

    results = chain.batch(
        [
            [SystemMessage(content=system_prompt), HumanMessage(content=item["prompt"])]
            for item in work_items
        ],
        config={"max_concurrency": 50},
        return_exceptions=True,
    )

    completed = 0
    skipped = 0
    failed = 0

    for item, result in zip(work_items, results):
        cell_id: str = item["cell_id"]
        group_id: str = item["group_id"]
        pass2_path: Path = item["pass2_path"]

        if isinstance(result, Exception):
            logger.error("[ERROR] New Pass 2 LLM call failed for cell %s: %s", cell_id, result)
            failed += 1
            continue

        pass2_cell_result: Pass2CellResult = result
        pass2_json = {
            "cell_id": cell_id,
            "group_id": group_id,
            "parameter_values": [pv.model_dump() for pv in pass2_cell_result.parameter_values],
        }
        save_json(pass2_path, pass2_json)
        logger.info("[PASS2_NEW_SAVED] %s (%d values)", cell_id, len(pass2_cell_result.parameter_values))

        # Log parameters where status is not_found
        for pv in pass2_cell_result.parameter_values:
            if pv.status == "not_found":
                logger.info(
                    "[VALUE_NOT_FOUND] cell %s | group %s | param %s",
                    cell_id, group_id, pv.parameter_id,
                )

        completed += 1

    logger.info(
        "New Pass 2 complete: %d completed, %d skipped, %d failed",
        completed, skipped, failed,
    )


# ---------------------------------------------------------------------------
# Extended run_all: includes 3P steps + new Pass 2
# ---------------------------------------------------------------------------

def run_all_extended(state: dict) -> None:
    """
    Run the full extended Phase 2 pipeline:
    form_groups → pass1 → 3p-classify → 3p-run → pass2 (new)
    """
    llm = _get_llm(LLM_SMART_MODEL)

    logger.info("========== Phase 2 Extended Start ==========")

    logger.info("--- Step 1: Form groups ---")
    groups = form_groups(state)

    logger.info("--- Step 2: Pass 1 (parameter structure) ---")
    run_pass1(state)

    logger.info("--- Step 3: 3P-classify (UNKNOWN classification + prompts) ---")
    run_3p_classify(groups=groups, data_root=COUNTRIES_DIR, llm=llm)

    logger.info("--- Step 4: 3P-execute (Parallel API drill-down) ---")
    run_3p_execute(groups=groups, data_root=COUNTRIES_DIR)

    logger.info("--- Step 5: New Pass 2 (parameter values per cell) ---")
    run_new_pass2(state=state, llm=llm)

    logger.info("========== Phase 2 Extended Complete ==========")


# ===========================================================================
# Pass 2 translation — translate pass2.json text fields to Russian
# ===========================================================================

def run_pass2_translate(llm: ChatOpenAI) -> None:
    """
    For each pass2.json file: translate text fields to Russian using LLM batch.
    parameter_name is substituted from PARAM_NAMES_RU dictionary (not translated via LLM).

    Saves pass2_ru.json in the same directory as pass2.json.
    Idempotency: skip if pass2_ru.json already exists.
    """
    logger.info("Starting Pass 2 translation to Russian")

    work_items: list[dict] = []

    for venue in PILOT_VENUES:
        name_ru = venue["name_ru"]
        venue_key = venue["venue_key"]
        level3_dir = get_country_level3_dir(name_ru, venue_key)
        if not level3_dir.exists():
            continue

        for cell_dir in sorted(level3_dir.iterdir()):
            if not cell_dir.is_dir():
                continue
            pass2_path = cell_dir / "pass2.json"
            pass2_ru_path = cell_dir / "pass2_ru.json"

            if not pass2_path.exists():
                continue

            if pass2_ru_path.exists():
                logger.info("[SKIP] pass2_ru.json already exists for %s", cell_dir.name)
                continue

            pass2_data = load_json(pass2_path)
            if not pass2_data:
                logger.warning("pass2.json empty for %s — skipping", cell_dir.name)
                continue

            work_items.append({
                "cell_id": cell_dir.name,
                "pass2_ru_path": pass2_ru_path,
                "pass2_data": pass2_data,
                "prompt": _build_translate_prompt(pass2_data),
            })

    if not work_items:
        logger.info("No cells need translation — all done or no pass2.json found")
        return

    logger.info("Running translation batch for %d cells", len(work_items))

    system_prompt = (
        "You are a professional translator specializing in financial and securities regulation. "
        "Translate the provided JSON data fields from English to Russian as instructed. "
        "Return ONLY valid JSON — no markdown, no explanations."
    )

    chain = llm.with_structured_output(Pass2CellResult)

    results = chain.batch(
        [
            [SystemMessage(content=system_prompt), HumanMessage(content=item["prompt"])]
            for item in work_items
        ],
        config={"max_concurrency": 50},
        return_exceptions=True,
    )

    completed = 0
    failed = 0

    for item, result in zip(work_items, results):
        cell_id: str = item["cell_id"]
        pass2_ru_path: Path = item["pass2_ru_path"]
        original_data: dict = item["pass2_data"]

        if isinstance(result, Exception):
            logger.error("[ERROR] Translation failed for cell %s: %s", cell_id, result)
            failed += 1
            continue

        translated: Pass2CellResult = result

        # Inject Russian parameter names from dictionary (override LLM output for parameter_name)
        # Also preserve source, linkages, drill_down_applied, status from original
        original_by_idx: dict[int, dict] = {
            i: pv for i, pv in enumerate(original_data.get("parameter_values", []))
        }

        parameter_values_ru = []
        for i, pv in enumerate(translated.parameter_values):
            pv_dict = pv.model_dump()
            orig = original_by_idx.get(i, {})
            # Override: parameter_name from dictionary (or original if not in dict)
            pv_dict["parameter_name"] = PARAM_NAMES_RU.get(pv.parameter_id, orig.get("parameter_name", pv.parameter_name))
            # Preserve source unchanged (do not translate)
            pv_dict["source"] = orig.get("source", pv.source)
            # Preserve linkages unchanged (they are parameter IDs)
            pv_dict["linkages"] = orig.get("linkages", pv.linkages)
            # Preserve structural fields unchanged
            pv_dict["drill_down_applied"] = orig.get("drill_down_applied", pv.drill_down_applied)
            pv_dict["status"] = orig.get("status", pv.status)
            pv_dict["lifecycle_phase"] = orig.get("lifecycle_phase", pv.lifecycle_phase)
            parameter_values_ru.append(pv_dict)

        save_json(pass2_ru_path, {
            "cell_id": original_data.get("cell_id", cell_id),
            "group_id": original_data.get("group_id", ""),
            "parameter_values": parameter_values_ru,
        })

        logger.info("[TRANSLATED] %s (%d params)", cell_id, len(parameter_values_ru))
        completed += 1

    logger.info(
        "Translation complete: %d translated, %d failed",
        completed, failed,
    )
