"""
Level 3 v2: LLM postprocessing — disaggregate Parallel results into per-cell files.

Input:  03_data/countries/{name_ru}/level_3/{venue_key}/_parallel_raw/{venue_key}_{instrument_class}_{query_type}_raw.json
        03_data/countries/{name_ru}/level_2/{venue_key}/cells_list.json
Output: 03_data/countries/{name_ru}/level_3/{venue_key}/{cell_id}/{query_type}_raw.json
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from pipeline.config import (
    LLM_SMART_MODEL,
    LLM_FAST_MODEL,
    LEVEL3_V2_LOG_FILE,
    PILOT_VENUES,
    get_country_level2_dir,
    get_country_level3_dir,
)
from pipeline.storage import load_json, save_json, now_iso
from pipeline.logging_setup import get_logger

logger = get_logger("postprocess_l3", LEVEL3_V2_LOG_FILE)


# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------

def _get_llm(model: str = LLM_FAST_MODEL) -> ChatOpenAI:
    return ChatOpenAI(model=model, api_key=os.environ["OPENAI_API_KEY"], temperature=0)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TierMapping(BaseModel):
    """Maps a tier_name from Parallel result to a cell_id from cells_list."""
    tier_name: str
    cell_id: str  # "not_found" if no matching cell


class TierMappingList(BaseModel):
    mappings: list[TierMapping]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cells_for_instrument_class(cells: list[dict], instrument_class: str) -> list[dict]:
    return [c for c in cells if c.get("instrument_class") == instrument_class]


def _build_mapping_prompt(
    tier_names: list[str],
    cells: list[dict],
    venue_key: str,
    instrument_class: str,
) -> str:
    """Build the prompt for tier_name → cell_id mapping."""
    cell_summaries = []
    for cell in cells:
        cell_summaries.append(
            f"  cell_id={cell.get('cell_id', '?')} | "
            f"tier={cell.get('tier', '?')} | "
            f"instrument_class={cell.get('instrument_class', '?')} | "
            f"legacy={cell.get('legacy', False)} | "
            f"admission_path={cell.get('admission_path', 'listing')}"
        )
    cells_str = "\n".join(cell_summaries)
    tiers_str = "\n".join(f"  - {t}" for t in tier_names)

    return f"""You are matching listing tier names from a research result to cell IDs from a structured venue database.

Venue: {venue_key}
Instrument class: {instrument_class}

TIER NAMES found in research result:
{tiers_str}

CELLS in database for this venue and instrument class:
{cells_str}

For each tier_name, identify the best matching cell_id.
Rules:
- Match by comparing tier_name to cell's tier field (fuzzy match, translations OK)
- If a tier_name represents a legacy/transition category, match to cell with legacy=True
- If no matching cell exists, use cell_id="not_found"
- Each cell_id should appear at most once in your output

Return a mapping for ALL tier names listed above."""


# ---------------------------------------------------------------------------
# Core disaggregation
# ---------------------------------------------------------------------------

def _disaggregate_one(
    raw_path: Path,
    cells: list[dict],
    venue_key: str,
    name_ru: str,
    instrument_class: str,
    query_type: str,
    llm: ChatOpenAI,
) -> None:
    """Disaggregate one raw Parallel result into per-cell files."""
    raw_data = load_json(raw_path)
    if raw_data is None:
        logger.warning("Raw file not found: %s — skipping", raw_path)
        return

    content = raw_data.get("content", {})
    if not isinstance(content, dict):
        logger.warning("Unexpected content format in %s — skipping", raw_path)
        return

    tiers = content.get("tiers", [])
    common_key = "common_requirements" if query_type == "3A" else (
        "common_obligations" if query_type == "3B" else "common_monitoring"
    )
    common_data = content.get(common_key, {})

    if not tiers:
        logger.warning("No tiers found in %s — skipping", raw_path)
        return

    # Filter cells to this instrument_class
    relevant_cells = _cells_for_instrument_class(cells, instrument_class)
    if not relevant_cells:
        logger.warning(
            "No cells for instrument_class=%s in venue %s — skipping", instrument_class, venue_key
        )
        return

    tier_names = [t.get("tier_name", f"tier_{i}") for i, t in enumerate(tiers)]

    # Use LLM to map tier_names to cell_ids
    mapping_prompt = _build_mapping_prompt(tier_names, relevant_cells, venue_key, instrument_class)
    chain = llm.with_structured_output(TierMappingList, method="function_calling")
    try:
        mapping_result: TierMappingList = chain.invoke([HumanMessage(content=mapping_prompt)])
        mappings = {m.tier_name: m.cell_id for m in mapping_result.mappings}
    except Exception as exc:
        logger.error("LLM mapping failed for %s: %s — using sequential fallback", raw_path.name, exc)
        # Fallback: map sequentially by index
        mappings = {}
        for i, tier in enumerate(tiers):
            if i < len(relevant_cells):
                mappings[tier.get("tier_name", f"tier_{i}")] = relevant_cells[i].get("cell_id", f"cell_{i}")

    # Save per-cell files
    base_dir = get_country_level3_dir(name_ru, venue_key)
    for tier_data in tiers:
        tier_name = tier_data.get("tier_name", "")
        cell_id = mappings.get(tier_name, "not_found")

        if cell_id == "not_found":
            logger.warning("No cell mapping for tier '%s' in %s — skipping", tier_name, raw_path.name)
            continue

        cell_dir = base_dir / cell_id
        cell_dir.mkdir(parents=True, exist_ok=True)
        out_path = cell_dir / f"{query_type}_raw.json"

        # Combine tier data with common fields
        combined_content = {**tier_data, f"{common_key}_common": common_data}
        out_data = {
            "cell_id": cell_id,
            "venue_key": venue_key,
            "instrument_class": instrument_class,
            "query_type": query_type,
            "tier_name_from_parallel": tier_name,
            "retrieved_at": raw_data.get("retrieved_at", now_iso()),
            "content": combined_content,
        }
        save_json(out_path, out_data)
        logger.info("Saved cell result: %s", out_path)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def postprocess_all_venues(state: dict) -> None:
    """
    Disaggregate all venue-level Parallel results into per-cell files.
    Iterates all pilot venues, finds completed raw results, disaggregates.
    """
    llm = _get_llm(LLM_FAST_MODEL)
    logger.info("Starting L3 postprocessing (tier disaggregation)")

    for venue in PILOT_VENUES:
        venue_key = venue["venue_key"]
        name_ru = venue["name_ru"]

        cells_path = get_country_level2_dir(name_ru, venue_key) / "cells_list.json"
        cells_data = load_json(cells_path)
        if not cells_data:
            logger.warning("cells_list.json not found for %s — skipping", venue_key)
            continue
        cells = cells_data.get("cells", [])

        raw_dir = get_country_level3_dir(name_ru, venue_key) / "_parallel_raw"
        if not raw_dir.exists():
            logger.info("No _parallel_raw dir for %s — skipping", venue_key)
            continue

        for raw_file in sorted(raw_dir.glob("*_raw.json")):
            # Parse filename: {venue_key}_{instrument_class}_{query_type}_raw.json
            stem = raw_file.stem  # e.g. LSE_Main_Market_equity_3A_raw → without extension
            # Remove trailing _raw
            if stem.endswith("_raw"):
                stem = stem[:-4]
            # Last part is query_type (3A/3B/3C), second-to-last is instrument_class
            # venue_key may contain underscores, so split from right
            parts = stem.rsplit("_", 2)
            if len(parts) != 3:
                logger.warning("Cannot parse filename %s — skipping", raw_file.name)
                continue
            _, instrument_class, query_type = parts

            logger.info(
                "Disaggregating %s / %s / %s", venue_key, instrument_class, query_type
            )
            _disaggregate_one(
                raw_path=raw_file,
                cells=cells,
                venue_key=venue_key,
                name_ru=name_ru,
                instrument_class=instrument_class,
                query_type=query_type,
                llm=llm,
            )

    logger.info("L3 postprocessing complete.")
