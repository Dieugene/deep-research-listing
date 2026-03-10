"""
Level 3 v2: LLM validation of disaggregated per-cell results.

Three checks per cell:
1. SCOPE CHECK — correct venue/tier/instrument_class, no foreign data
2. COMPLETENESS CHECK — expected topics present for this instrument class
3. SOURCE CHECK — rulebook chapters match expected for this tier

Output: {cell_id}/validation_report.json per cell
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from pipeline.config import (
    LLM_FAST_MODEL,
    LEVEL3_V2_LOG_FILE,
    PILOT_VENUES,
    get_country_level2_dir,
    get_country_level3_dir,
)
from pipeline.storage import load_json, save_json, now_iso
from pipeline.logging_setup import get_logger

logger = get_logger("validator_l3", LEVEL3_V2_LOG_FILE)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ValidationReport(BaseModel):
    cell_id: str
    query_type: str
    scope_ok: bool
    scope_issues: list[str]
    completeness_score: float  # 0.0 to 1.0
    missing_topics: list[str]
    source_ok: bool
    suspicious_sources: list[str]
    overall_flag: bool  # True = needs review
    notes: str


# ---------------------------------------------------------------------------
# Completeness checklists by instrument class
# ---------------------------------------------------------------------------

_COMPLETENESS_CHECKLIST = {
    "equity": [
        "free float", "market capitalisation", "financial history",
        "profitability/revenue test", "corporate governance", "sponsor/nomad",
        "prospectus/admission document", "lock-up periods",
    ],
    "bond": [
        "minimum issue size", "issuer eligibility", "prospectus",
        "listing documentation", "disclosure requirements",
    ],
    "fund": [
        "NAV/AUM requirements", "fund structure", "management company",
        "investment policy", "prospectus",
    ],
    "depositary_receipt": [
        "underlying security requirements", "depositary bank",
        "prospectus/listing document", "issuer eligibility",
    ],
}


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_validation_prompt(
    cell_result: dict,
    cell: dict,
    venue_card: dict,
    venue_key: str,
    query_type: str,
) -> str:
    instrument_class = cell.get("instrument_class", "")
    tier_name = cell.get("tier", "")
    other_tiers = [
        t.get("tier_name_ru") or t.get("tier_name", "")
        for t in venue_card.get("tiers", [])
        if (t.get("tier_name_ru") or t.get("tier_name", "")) != tier_name
    ]
    checklist = _COMPLETENESS_CHECKLIST.get(instrument_class, [])
    checklist_str = "\n".join(f"  - {item}" for item in checklist)
    other_tiers_str = ", ".join(other_tiers) if other_tiers else "none"

    result_str = json.dumps(cell_result.get("content", {}), ensure_ascii=False, indent=2)[:3000]

    return f"""You are validating a research result for accuracy and completeness.

TARGET: cell_id={cell.get('cell_id')}, tier='{tier_name}', instrument_class={instrument_class}, venue={venue_key}, query_type={query_type}

OTHER TIERS on this venue (data about these should NOT be in this result): {other_tiers_str}

RESEARCH RESULT (truncated to 3000 chars):
{result_str}

Perform THREE checks:

1. SCOPE CHECK: Does the result contain information about the correct venue, tier, and instrument class?
   Are there references to other tiers/categories/venues that should not be here?
   Answer: scope_ok=true/false, list any scope_issues found.

2. COMPLETENESS CHECK for {instrument_class} {query_type} on {venue_key}:
   Expected topics:
{checklist_str}
   Which are present? Which are missing?
   Answer: completeness_score (0.0=none present, 1.0=all present), missing_topics list.

3. SOURCE CHECK: Do the cited rulebook chapters correspond to the tier '{tier_name}'?
   Flag any sources that appear to belong to a different tier/category (e.g., wrong UKLR category for UK listings).
   Answer: source_ok=true/false, list suspicious_sources.

Set overall_flag=true if any check failed (scope_ok=false OR completeness_score < 0.5 OR source_ok=false).
Add a brief notes field summarising the main issues."""


# ---------------------------------------------------------------------------
# Single-cell validation (used for invoke path, kept for reference)
# ---------------------------------------------------------------------------

def _validate_one(
    cell: dict,
    query_type: str,
    venue_key: str,
    name_ru: str,
    venue_card: dict,
    llm: ChatOpenAI,
) -> Optional[ValidationReport]:
    cell_id = cell.get("cell_id", "")
    cell_dir = get_country_level3_dir(name_ru, venue_key) / cell_id
    result_path = cell_dir / f"{query_type}_raw.json"

    if not result_path.exists():
        logger.debug("No result file for cell %s %s — skipping validation", cell_id, query_type)
        return None

    cell_result = load_json(result_path)
    if not cell_result:
        logger.warning("Failed to load %s — skipping validation", result_path)
        return None

    prompt = _build_validation_prompt(cell_result, cell, venue_card, venue_key, query_type)
    chain = llm.with_structured_output(ValidationReport, method="function_calling")
    try:
        report: ValidationReport = chain.invoke([HumanMessage(content=prompt)])
        # Ensure cell_id and query_type are set
        report.cell_id = cell_id
        report.query_type = query_type
        return report
    except Exception as exc:
        logger.error("Validation LLM call failed for %s %s: %s", cell_id, query_type, exc)
        return None


# ---------------------------------------------------------------------------
# Batch validation for a venue
# ---------------------------------------------------------------------------

def _validate_venue(
    venue_key: str,
    name_ru: str,
    cells: list[dict],
    venue_card: dict,
    llm: ChatOpenAI,
) -> None:
    """Validate all cells for a venue using batch LLM calls."""
    # Build (cell, query_type) pairs that have result files
    pairs = []
    for cell in cells:
        cell_id = cell.get("cell_id", "")
        cell_dir = get_country_level3_dir(name_ru, venue_key) / cell_id
        for qt in ("3A", "3B", "3C"):
            if (cell_dir / f"{qt}_raw.json").exists():
                pairs.append((cell, qt))

    if not pairs:
        logger.info("No result files found for %s — skipping validation", venue_key)
        return

    logger.info("Validating %d cell/query_type pairs for %s", len(pairs), venue_key)

    # Build prompts for batch
    prompts = []
    for cell, qt in pairs:
        cell_id = cell.get("cell_id", "")
        cell_dir = get_country_level3_dir(name_ru, venue_key) / cell_id
        cell_result = load_json(cell_dir / f"{qt}_raw.json") or {}
        prompt = _build_validation_prompt(cell_result, cell, venue_card, venue_key, qt)
        prompts.append(prompt)

    chain = llm.with_structured_output(ValidationReport, method="function_calling")

    # CRITICAL: use [[HumanMessage(content=p)] for p in prompts]
    results = chain.batch(
        [[HumanMessage(content=p)] for p in prompts],
        config={"max_concurrency": 50},
        return_exceptions=True,
    )

    # Save reports
    for (cell, qt), result in zip(pairs, results):
        cell_id = cell.get("cell_id", "")
        if isinstance(result, Exception):
            logger.error("Validation failed for %s %s: %s", cell_id, qt, result)
            continue

        report = result
        report.cell_id = cell_id
        report.query_type = qt

        cell_dir = get_country_level3_dir(name_ru, venue_key) / cell_id
        report_path = cell_dir / f"{qt}_validation.json"
        save_json(report_path, report.model_dump())

        if report.overall_flag:
            logger.warning(
                "REVIEW NEEDED: %s %s — scope=%s completeness=%.2f source=%s",
                cell_id, qt, report.scope_ok, report.completeness_score, report.source_ok
            )
        else:
            logger.info("OK: %s %s (completeness=%.2f)", cell_id, qt, report.completeness_score)


# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------

def _get_llm(model: str = LLM_FAST_MODEL) -> ChatOpenAI:
    return ChatOpenAI(model=model, api_key=os.environ["OPENAI_API_KEY"], temperature=0)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def validate_all_venues(state: dict) -> None:
    """Run validation for all pilot venues."""
    llm = _get_llm(LLM_FAST_MODEL)
    logger.info("Starting L3 validation")

    for venue in PILOT_VENUES:
        venue_key = venue["venue_key"]
        name_ru = venue["name_ru"]

        cells_path = get_country_level2_dir(name_ru, venue_key) / "cells_list.json"
        cells_data = load_json(cells_path)
        if not cells_data:
            logger.warning("cells_list.json not found for %s", venue_key)
            continue
        cells = cells_data.get("cells", [])

        venue_card_path = get_country_level2_dir(name_ru, venue_key) / "venue_card.json"
        venue_card = load_json(venue_card_path) or {}

        _validate_venue(venue_key, name_ru, cells, venue_card, llm)

    logger.info("L3 validation complete.")
