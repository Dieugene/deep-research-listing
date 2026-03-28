"""
Level 3 v2: LLM postprocessing — disaggregate Parallel results into per-cell files.

Input:  03_data/countries/{name_ru}/level_3/{venue_key}/_parallel_raw/{venue_key}_{instrument_class}_{query_type}_raw.json
        03_data/countries/{name_ru}/level_2/{venue_key}/cells_list.json
        (optional) 03_data/countries/{name_ru}/level_3/{venue_key}/_parallel_raw/{venue_key}_{instrument_class}_tier_map.json
Output: 03_data/countries/{name_ru}/level_3/{venue_key}/{cell_id}/{query_type}_raw.json

When a canonical tier_map.json exists (produced by tier_mapper.py), it is used
directly instead of running per-file LLM mapping.  This ensures consistent
tier→cell_id assignment across 3A/3B/3C queries.
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
    INSTRUMENT_CLASSES,
    COUNTRIES_DIR,
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
# Canonical tier-map helpers
# ---------------------------------------------------------------------------

def _normalize_for_match(s: str) -> str:
    """Normalize string for fuzzy tier matching: lowercase, collapse dashes/whitespace."""
    import re as _re
    s = s.lower().strip()
    # Normalize all dash variants (en-dash, em-dash, hyphen) to a single hyphen
    s = _re.sub(r"[\u2013\u2014\u2012\u2015-]+", "-", s)
    # Collapse whitespace
    s = _re.sub(r"\s+", " ", s)
    return s


def _find_cell_for_canonical(
    canonical: dict,
    cells: list[dict],
    instrument_class: str,
) -> str | None:
    """Find the best matching cell_id for a canonical tier entry."""
    canonical_name = canonical.get("canonical_name", "")
    canonical_id = canonical.get("canonical_id", "")

    ic_cells = [c for c in cells if c.get("instrument_class") == instrument_class]

    cn_norm = _normalize_for_match(canonical_name)

    # Strategy 1: exact tier name match (normalized)
    for cell in ic_cells:
        if _normalize_for_match(cell.get("tier", "")) == cn_norm:
            return cell["cell_id"]

    # Strategy 2: cell tier contained in canonical_name or vice versa
    # Use alphanumeric-only comparison to handle dash/punctuation differences
    import re as _re
    cn_alpha = _re.sub(r"\s+", " ", _re.sub(r"[^a-z0-9 ]", "", cn_norm)).strip()
    for cell in ic_cells:
        cell_tier_norm = _normalize_for_match(cell.get("tier", ""))
        cell_alpha = _re.sub(r"\s+", " ", _re.sub(r"[^a-z0-9 ]", "", cell_tier_norm)).strip()
        if len(cn_alpha) > 3 and len(cell_alpha) > 3:
            if cn_alpha in cell_alpha or cell_alpha in cn_alpha:
                return cell["cell_id"]

    # Strategy 3: canonical_id slug matches part of cell_id
    for cell in ic_cells:
        cell_id_lower = cell["cell_id"].lower().replace("_", "")
        canon_slug = canonical_id.lower().replace("_", "")
        if canon_slug and len(canon_slug) > 3 and canon_slug in cell_id_lower:
            return cell["cell_id"]

    # Strategy 4: if only 1 flat cell for this IC, use it
    if len(ic_cells) == 1:
        cell_tier = ic_cells[0].get("tier", "")
        if cell_tier.startswith("(no listing") or cell_tier == "flat":
            return ic_cells[0]["cell_id"]

    return None


def _load_canonical_mapping(
    venue_dir: Path,
    venue_key: str,
    instrument_class: str,
    query_type: str,
    relevant_cells: list[dict],
) -> dict[str, str] | None:
    """
    Load tier_map.json and build {tier_name → cell_id} for this query_type.

    Only includes tiers with belongs_to_venue=True.
    Returns None if no tier_map exists (triggers LLM fallback).
    """
    par_raw = venue_dir / "_parallel_raw"
    map_file = par_raw / f"{venue_key}_{instrument_class}_tier_map.json"
    if not map_file.exists():
        return None

    try:
        with open(map_file, encoding="utf-8") as f:
            tier_map = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("Failed to read tier_map %s — falling back to LLM", map_file)
        return None

    qt_key = f"tier_{query_type.lower()}"  # "tier_3a", "tier_3b", "tier_3c"

    mapping: dict[str, str] = {}
    unmatched: list[str] = []

    for canonical in tier_map.get("tiers", []):
        if not canonical.get("belongs_to_venue", False):
            continue

        tier_name = canonical.get(qt_key, "")
        if not tier_name:
            continue

        # Skip if this tier_name was already mapped (merged_in_3c case)
        if tier_name in mapping:
            continue

        cell_id = _find_cell_for_canonical(canonical, relevant_cells, instrument_class)
        if cell_id:
            mapping[tier_name] = cell_id
        else:
            unmatched.append(
                f"{canonical.get('canonical_name', '?')} (tier_name={tier_name!r})"
            )

    if unmatched:
        logger.warning(
            "Canonical tiers without matching cell in %s / %s: %s",
            venue_key, instrument_class, "; ".join(unmatched),
        )

    return mapping if mapping else None


# ---------------------------------------------------------------------------
# Save disaggregated per-cell files
# ---------------------------------------------------------------------------

def _save_disaggregated(item: dict, mappings: dict[str, str]) -> None:
    """Save per-cell files for a single work item using the provided tier→cell_id mappings."""
    venue_key = item["venue_key"]
    name_ru = item["name_ru"]
    instrument_class = item["instrument_class"]
    query_type = item["query_type"]
    tiers = item["tiers"]
    common_key = item["common_key"]
    common_data = item["common_data"]
    raw_data = item["raw_data"]

    base_dir = get_country_level3_dir(name_ru, venue_key)
    for tier_data in tiers:
        tier_name = tier_data.get("tier_name", "")
        cell_id = mappings.get(tier_name, "not_found")

        if cell_id == "not_found":
            logger.warning(
                "No cell mapping for tier '%s' in %s / %s — skipping",
                tier_name, venue_key, instrument_class,
            )
            continue

        cell_dir = base_dir / cell_id
        cell_dir.mkdir(parents=True, exist_ok=True)
        out_path = cell_dir / f"{query_type}_raw.json"

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
    Collects all mapping tasks upfront, sends a single chain.batch() call,
    then saves per-cell files from the results.
    """
    llm = _get_llm(LLM_FAST_MODEL)
    chain = llm.with_structured_output(TierMappingList, method="function_calling")
    logger.info("Starting L3 postprocessing (tier disaggregation)")

    # --- Pass 1: collect all work items ---
    # Each work_item: {
    #   raw_path, venue_key, name_ru, instrument_class, query_type,
    #   tiers, common_key, common_data, relevant_cells, mapping_prompt
    # }
    work_items = []

    from pipeline.registry import discover_all_venues, load_jurisdictions
    _all_venues = discover_all_venues(load_jurisdictions(), COUNTRIES_DIR)

    # Filter out deferred venues
    _deferred_venue_keys = {
        v["venue_key"] for v in _all_venues
        if v.get("research_priority") == "deferred"
    }
    if _deferred_venue_keys:
        logger.info(
            "Deferred venues filter: %d venues will be skipped", len(_deferred_venue_keys)
        )
    _all_venues = [v for v in _all_venues if v["venue_key"] not in _deferred_venue_keys]

    for venue in _all_venues:
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
            stem = raw_file.stem
            if stem.endswith("_raw"):
                stem = stem[:-4]
            query_type = stem.rsplit("_", 1)[1]
            prefix = stem.rsplit("_", 1)[0]
            instrument_class = None
            for ic in sorted(INSTRUMENT_CLASSES, key=len, reverse=True):
                if prefix.endswith(f"_{ic}"):
                    instrument_class = ic
                    break
            if instrument_class is None:
                logger.warning("Cannot parse filename %s — skipping", raw_file.name)
                continue

            raw_data = load_json(raw_file)
            if raw_data is None:
                logger.warning("Raw file not found: %s — skipping", raw_file)
                continue

            if "parallel_output" in raw_data:
                content = raw_data["parallel_output"].get("content", {})
            else:
                content = raw_data.get("content", {})
            if not isinstance(content, dict):
                logger.warning("Unexpected content format in %s — skipping", raw_file)
                continue
            # Handle nested parallel_output structure: content may be the full
            # parallel_output wrapper {basis, content, type, ...} rather than
            # the actual research data. Unwrap if needed.
            if "basis" in content and "content" in content and "type" in content:
                inner = content.get("content", {})
                if isinstance(inner, dict):
                    content = inner

            tiers = content.get("tiers", [])
            if not tiers:
                logger.warning("No tiers found in %s — skipping", raw_file)
                continue

            common_key = (
                "common_requirements" if query_type == "3A"
                else "common_obligations" if query_type == "3B"
                else "common_monitoring"
            )
            common_data = content.get(common_key, {})

            relevant_cells = _cells_for_instrument_class(cells, instrument_class)
            if not relevant_cells:
                logger.warning(
                    "No cells for instrument_class=%s in venue %s — skipping",
                    instrument_class, venue_key,
                )
                continue

            tier_names = [t.get("tier_name", f"tier_{i}") for i, t in enumerate(tiers)]

            # --- Try canonical tier_map first ---
            venue_dir = get_country_level3_dir(name_ru, venue_key)
            canonical_mapping = _load_canonical_mapping(
                venue_dir=venue_dir,
                venue_key=venue_key,
                instrument_class=instrument_class,
                query_type=query_type,
                relevant_cells=relevant_cells,
            )

            if canonical_mapping is not None:
                logger.info(
                    "Using canonical tier_map for %s / %s / %s (%d mappings)",
                    venue_key, instrument_class, query_type, len(canonical_mapping),
                )
                work_items.append({
                    "raw_path": raw_file,
                    "raw_data": raw_data,
                    "venue_key": venue_key,
                    "name_ru": name_ru,
                    "instrument_class": instrument_class,
                    "query_type": query_type,
                    "tiers": tiers,
                    "common_key": common_key,
                    "common_data": common_data,
                    "relevant_cells": relevant_cells,
                    "mapping_prompt": None,
                    "canonical_mapping": canonical_mapping,
                })
            else:
                # Fallback: use LLM mapping (legacy behavior)
                mapping_prompt = _build_mapping_prompt(
                    tier_names, relevant_cells, venue_key, instrument_class,
                )
                work_items.append({
                    "raw_path": raw_file,
                    "raw_data": raw_data,
                    "venue_key": venue_key,
                    "name_ru": name_ru,
                    "instrument_class": instrument_class,
                    "query_type": query_type,
                    "tiers": tiers,
                    "common_key": common_key,
                    "common_data": common_data,
                    "relevant_cells": relevant_cells,
                    "mapping_prompt": mapping_prompt,
                    "canonical_mapping": None,
                })

    if not work_items:
        logger.info("No raw files found to disaggregate.")
        return

    # --- Separate canonical vs LLM items ---
    canonical_items = [w for w in work_items if w.get("canonical_mapping") is not None]
    llm_items = [w for w in work_items if w.get("canonical_mapping") is None]

    logger.info(
        "Collected %d mapping tasks: %d canonical (tier_map), %d LLM",
        len(work_items), len(canonical_items), len(llm_items),
    )

    # --- LLM batch call (only for items without canonical mapping) ---
    llm_results: list = []
    if llm_items:
        logger.info("Running batch LLM call for %d items", len(llm_items))
        prompts = [item["mapping_prompt"] for item in llm_items]
        llm_results = chain.batch(
            [[HumanMessage(content=p)] for p in prompts],
            config={"max_concurrency": 50},
            return_exceptions=True,
        )

    # --- Pass 2: apply mappings and save per-cell files ---

    # Process canonical items first
    for item in canonical_items:
        mappings = item["canonical_mapping"]
        _save_disaggregated(item, mappings)

    # Process LLM items
    for item, result in zip(llm_items, llm_results):
        venue_key = item["venue_key"]
        instrument_class = item["instrument_class"]
        query_type = item["query_type"]
        tiers = item["tiers"]
        relevant_cells = item["relevant_cells"]

        if isinstance(result, Exception):
            logger.error(
                "LLM mapping failed for %s / %s / %s: %s — using index fallback",
                venue_key, instrument_class, query_type, result,
            )
            mappings = {
                t.get("tier_name", f"tier_{i}"): relevant_cells[i].get("cell_id", f"cell_{i}")
                for i, t in enumerate(tiers)
                if i < len(relevant_cells)
            }
        else:
            mappings = {m.tier_name: m.cell_id for m in result.mappings}

        _save_disaggregated(item, mappings)

    logger.info("L3 postprocessing complete.")
