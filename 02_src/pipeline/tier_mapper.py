"""
Canonical tier mapping for L3 pipeline.

Reconciles tier/category structures returned by three independent research
queries (3A, 3B, 3C) about the same venue x instrument_class into a unified
canonical tier map using an LLM.

Saves results as {venue}_{instrument_class}_tier_map.json in _parallel_raw.
"""
import datetime
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from pipeline.config import COUNTRIES_DIR, LOGS_DIR, LLM_SMART_MODEL
from pipeline.logging_setup import get_logger

logger = get_logger(
    "tier_mapper",
    LOGS_DIR / f"tier_mapper_{datetime.date.today()}.log",
)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class TierMapping(BaseModel):
    canonical_id: str
    canonical_name: str
    belongs_to_venue: bool
    other_venue_hint: str = ""
    tier_3a: str = ""
    tier_3b: str = ""
    tier_3c: str = ""
    merged_in_3c: bool = False
    sources_regulatory_framework: str = ""


class TierCanonicalMap(BaseModel):
    tiers: list[TierMapping]
    venue_card_update_needed: bool = False
    notes: str = ""


# ---------------------------------------------------------------------------
# JSON helpers (atomic write)
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> Optional[dict]:
    """Load JSON from path; return None if missing or empty."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return None


def _save_json(path: Path, data: dict) -> None:
    """Atomically write JSON to path using tempfile + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# System prompt (from architect spec)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a regulatory analyst specializing in securities listing rules.
Your task is to reconcile tier/category structures returned by three
independent research queries about the same trading venue.

CONTEXT OF THE PROBLEM:
Three separate research queries (3A — primary admission,
3B — maintenance/suspension/delisting, 3C — monitoring/enforcement)
were sent to investigate the same instrument class on the same venue.
Each query independently found and named tiers/categories. The results
differ because:
- Different research queries surface different aspects of regulation.
  Admission rules may distinguish General Standard from Prime Standard
  (different thresholds), while monitoring rules may treat them as one
  (same enforcement regime). This is NOT an error — it reflects how
  regulation is actually structured.
- Tier names may vary between queries for the same tier
  (e.g., "General Standard" vs "Regulated Market – General Standard").
- A query may include tiers that belong to a DIFFERENT venue
  (different regulatory status), because the research engine found
  them relevant in context.

Your job: produce a CANONICAL LIST of unique tiers — a unified view
across all three queries.

DEFINITIONS — apply strictly:

TRADING VENUE: A market with its own regulatory framework and its own
set of admission/listing rules, operating under its own regulatory
status (e.g., EU Regulated Market, MTF, exchange-regulated market /
Freiverkehr).
TEST: if two markets have DIFFERENT regulatory classifications — they
are SEPARATE VENUES, even if operated by the same entity.
Examples:
- Frankfurt Regulated Market (Regulierter Markt) and Frankfurt Open
  Market (Freiverkehr) = two separate venues
- LSE Main Market (Regulated Market) and AIM (MTF) = two separate venues

LISTING TIER: A hierarchical level WITHIN a single venue that
determines the stringency of requirements. All tiers of one venue
share the SAME regulatory status and the SAME rulebook (or sections
of the same rulebook), but set DIFFERENT thresholds.
TEST: do the two levels share the same regulatory status? If yes —
they are tiers of one venue. If they have different regulatory
status — they are separate venues, not tiers.
Examples:
- General Standard and Prime Standard on Frankfurt Regulated Market
  = two tiers (same regulatory status, different transparency)
- Scale and Basic Board on Frankfurt = NOT tiers of Regulated Market
  (they are Freiverkehr — different regulatory status)

INSTRUMENT-CLASS ORGANIZATION: Some venues organize their rulebook
into chapters by instrument type (equities chapter, bonds chapter).
These are NOT tiers — they define which instruments are available,
not a hierarchy of stringency. Do not report them as tiers."""


# ---------------------------------------------------------------------------
# User prompt builder
# ---------------------------------------------------------------------------

_USER_PROMPT_TEMPLATE = """\
VENUE BEING ANALYZED:
  Name: {venue_name_english}
  Regulatory status / type: {venue_type}
  Operator: {operator}
  Jurisdiction: {jurisdiction}
  Instrument class: {instrument_class}

PRIOR KNOWLEDGE (from Level 2 venue card):
  Tiers found at L2: {venue_card_tiers_json}
  Segments: {venue_card_segments_json}
  Listing architecture: {venue_card_listing_architecture}

Note: L2 may have recorded "flat" (no tiers). If the queries below \
found actual tiers -- the queries are more detailed. Use the query \
data, not the L2 data, as the source of truth.

---

DATA FROM THREE RESEARCH QUERIES:

Each query returned an array of "tiers" with content. \
The tier structures may differ between queries -- this is expected.

=== QUERY 3A (Primary Admission Requirements) ===
{tier_data_3a}

=== QUERY 3B (Continuing Obligations / Suspension / Delisting) ===
{tier_data_3b}

=== QUERY 3C (Monitoring / Enforcement) ===
{tier_data_3c}

---

TASK:

Analyze all tiers across 3A, 3B, 3C and produce a canonical map.

Step 1. IDENTIFY UNIQUE TIERS.
Look at tier names AND content across all three queries. Two entries \
with different names may be the same tier (e.g., "General Standard" \
in 3A and "Regulated Market -- General Standard" in 3B). Two entries \
with similar names may be different tiers. Use content to decide.

Step 2. FOR EACH UNIQUE TIER, DETERMINE:

a) canonical_id -- lowercase snake_case slug \
   (e.g., "general_standard", "prime_standard", "flat")

b) canonical_name -- human-readable, with regulatory framework \
   in parentheses if helpful \
   (e.g., "General Standard (Regulierter Markt)")

c) belongs_to_venue -- does this tier belong to {venue_name_english} \
   ({venue_type})?
   Apply the regulatory status test from the definitions. \
   If the tier's content references regulations of a DIFFERENT \
   regulatory framework than {venue_type} -- it belongs to \
   a different venue.
   - true = belongs to the current venue
   - false = belongs to a different venue

d) other_venue_hint -- if belongs_to_venue is false: what venue \
   does it likely belong to? \
   (e.g., "Freiverkehr (Open Market)" or "AIM (MTF)")

e) tier_3a -- the EXACT tier name in 3A that maps to this \
   canonical tier. Empty string if absent from 3A.

f) tier_3b -- same for 3B.

g) tier_3c -- same for 3C.

h) merged_in_3c -- true if 3C combined this tier with one or more \
   other tiers into a single entry (common for monitoring/enforcement \
   that applies equally across tiers). If true, the same tier_3c \
   value will appear for multiple canonical tiers.

i) sources_regulatory_framework -- which regulatory framework do \
   the sources in this tier's content reference? This helps verify \
   venue belonging. \
   (e.g., "BorsG, BorsO FWB (Regulated Market rules)" or \
   "AGB Freiverkehr (Open Market rules)")

Step 3. CHECK FOR COMPLETENESS.
If a canonical tier has data in 3A but not in 3B -- this means \
the maintenance/delisting research did not find a separate entry \
for this tier. This is a data gap to note, not a reason to \
exclude the tier.

Step 4. DETERMINE IF VENUE CARD NEEDS UPDATE.
If L2 recorded "flat" or fewer tiers than you found -- \
venue_card_update_needed = true.

RESPOND WITH JSON ONLY (no markdown fences, no preamble):

{{
  "tiers": [
    {{
      "canonical_id": "string",
      "canonical_name": "string",
      "belongs_to_venue": true,
      "other_venue_hint": "string -- empty if belongs_to_venue is true",
      "tier_3a": "string -- exact name from 3A, or empty",
      "tier_3b": "string -- exact name from 3B, or empty",
      "tier_3c": "string -- exact name from 3C, or empty",
      "merged_in_3c": false,
      "sources_regulatory_framework": "string"
    }}
  ],
  "venue_card_update_needed": false,
  "notes": "string -- observations: naming discrepancies resolved, \
    data gaps (tier present in one query but not another), \
    ambiguous cases"
}}"""


# ---------------------------------------------------------------------------
# Tier overview extraction
# ---------------------------------------------------------------------------

# Sections to try for each query type, in priority order
_SECTIONS_3A = [
    ("admission_overview",),
    ("eligibility_requirements",),
    ("instrument_requirements",),
    ("procedure_and_timeline",),
    ("disclosure_at_admission",),
]

_SECTIONS_3B = [
    ("continuing_obligations", "quantitative_thresholds"),
    ("suspension", "grounds"),
    ("delisting_compulsory", "grounds"),
    ("continuing_obligations", "periodic_reporting"),
    ("continuing_obligations", "qualitative_obligations"),
]

_SECTIONS_3C = [
    ("monitoring_regime", "responsible_body"),
    ("sanctions", "exchange_sanctions"),
    ("enforcement_practice", "general_approach"),
    ("monitoring_regime", "mechanisms"),
    ("sanctions", "regulator_sanctions"),
]


def _get_tier_overview(tier_data: dict, query_type: str) -> tuple[str, str]:
    """Extract (description, source) for a tier's most informative section.

    For 3A: try admission_overview, eligibility_requirements, instrument_requirements
    For 3B: try continuing_obligations.quantitative_thresholds, suspension.grounds, etc.
    For 3C: try monitoring_regime.responsible_body, sanctions.exchange_sanctions, etc.

    Returns first non-empty (description, source) pair found.
    """
    if query_type == "3A":
        sections = _SECTIONS_3A
    elif query_type == "3B":
        sections = _SECTIONS_3B
    elif query_type == "3C":
        sections = _SECTIONS_3C
    else:
        sections = _SECTIONS_3A

    for path in sections:
        node = tier_data
        for key in path:
            if isinstance(node, dict):
                node = node.get(key)
            else:
                node = None
                break
        if isinstance(node, dict):
            desc = node.get("description", "")
            src = node.get("source", "")
            if desc and desc.strip():
                return (desc.strip(), src.strip() if src else "")

    return ("", "")


def _format_tier_data(tiers: list[dict], query_type: str) -> str:
    """Format tier list for the user prompt."""
    if not tiers:
        return "(no tiers found)"

    lines = []
    for tier in tiers:
        tier_name = tier.get("tier_name", "(unnamed)")
        desc, src = _get_tier_overview(tier, query_type)
        lines.append(f'Tier: "{tier_name}"')
        if desc:
            # Truncate long descriptions for prompt efficiency
            if len(desc) > 500:
                desc = desc[:500] + "..."
            lines.append(f"  Overview: {desc}")
        if src:
            lines.append(f"  Source: {src}")
        lines.append("")

    return "\n".join(lines).strip()


def _build_tier_mapping_prompt(
    venue_card: dict,
    tiers_3a: list[dict],
    tiers_3b: list[dict],
    tiers_3c: list[dict],
    instrument_class: str,
) -> str:
    """Build user prompt from venue card and tier data."""
    tiers_json = json.dumps(venue_card.get("tiers", []), ensure_ascii=False)
    segments_json = json.dumps(venue_card.get("segments", []), ensure_ascii=False)
    architecture = venue_card.get("listing_architecture", "unknown")
    if isinstance(architecture, list):
        architecture = json.dumps(architecture, ensure_ascii=False)

    return _USER_PROMPT_TEMPLATE.format(
        venue_name_english=venue_card.get("venue_name_english", "Unknown"),
        venue_type=venue_card.get("venue_type", "unknown"),
        operator=venue_card.get("operator", "unknown"),
        jurisdiction=venue_card.get("jurisdiction", venue_card.get("jurisdiction_ru", "unknown")),
        instrument_class=instrument_class,
        venue_card_tiers_json=tiers_json,
        venue_card_segments_json=segments_json,
        venue_card_listing_architecture=architecture,
        tier_data_3a=_format_tier_data(tiers_3a, "3A"),
        tier_data_3b=_format_tier_data(tiers_3b, "3B"),
        tier_data_3c=_format_tier_data(tiers_3c, "3C"),
    )


# ---------------------------------------------------------------------------
# Discovery: find all venue x instrument_class groups in _parallel_raw
# ---------------------------------------------------------------------------

_RAW_FILE_PATTERN = re.compile(
    r"^(.+?)_(equity|bond|fund|depositary_receipt)_(3[ABC])_raw\.json$"
)


def _discover_groups(
    jurisdictions: Optional[list[str]] = None,
) -> list[dict]:
    """
    Find all (venue_key, instrument_class) groups in _parallel_raw dirs.

    Returns list of dicts:
      {
        "jurisdiction_ru": str,
        "venue_key": str,
        "instrument_class": str,
        "raw_dir": Path,
        "files": {"3A": Path, "3B": Path, "3C": Path},
      }
    """
    groups: list[dict] = []

    for juris_dir in sorted(COUNTRIES_DIR.iterdir()):
        if not juris_dir.is_dir():
            continue
        if jurisdictions and juris_dir.name not in jurisdictions:
            continue

        l3_dir = juris_dir / "level_3"
        if not l3_dir.exists():
            continue

        for venue_dir in sorted(l3_dir.iterdir()):
            if not venue_dir.is_dir() or venue_dir.name.startswith("_"):
                continue

            raw_dir = venue_dir / "_parallel_raw"
            if not raw_dir.exists():
                continue

            # Group files by (venue_key, instrument_class)
            file_map: dict[tuple[str, str], dict[str, Path]] = {}

            for fpath in sorted(raw_dir.iterdir()):
                m = _RAW_FILE_PATTERN.match(fpath.name)
                if not m:
                    continue
                venue_key = m.group(1)
                ic = m.group(2)
                query_type = m.group(3)
                key = (venue_key, ic)
                if key not in file_map:
                    file_map[key] = {}
                file_map[key][query_type] = fpath

            for (venue_key, ic), files in file_map.items():
                # Need at least 2 of 3 query types to attempt mapping
                if len(files) < 2:
                    continue
                groups.append({
                    "jurisdiction_ru": juris_dir.name,
                    "venue_key": venue_key,
                    "instrument_class": ic,
                    "raw_dir": raw_dir,
                    "files": files,
                })

    return groups


# ---------------------------------------------------------------------------
# Load venue card
# ---------------------------------------------------------------------------


def _load_venue_card(jurisdiction_ru: str, venue_key: str) -> dict:
    """Load venue_card.json for a venue. Returns empty dict if not found."""
    # Try level_2 first (standard location)
    card_path = COUNTRIES_DIR / jurisdiction_ru / "level_2" / venue_key / "venue_card.json"
    if card_path.exists():
        return _load_json(card_path) or {}

    # Fallback: check venue dirs that match
    l2_dir = COUNTRIES_DIR / jurisdiction_ru / "level_2"
    if l2_dir.exists():
        for d in l2_dir.iterdir():
            if d.is_dir():
                cp = d / "venue_card.json"
                if cp.exists():
                    data = _load_json(cp) or {}
                    if data.get("venue_key") == venue_key:
                        return data

    return {}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Step 3.6: Update cells_list.json from tier_map results
# ---------------------------------------------------------------------------


def update_cells_list_from_tier_maps(
    jurisdictions: list[str] | None = None,
) -> None:
    """
    Update cells_list.json for each venue based on tier_map.json files.

    For each venue:
    1. Load all tier_map files (one per instrument_class)
    2. For each canonical tier with belongs_to_venue=True:
       - Check if a matching cell exists in cells_list
       - If not, create a new cell entry
       - If exists but tier name is "(no listing tiers — flat structure)",
         update the tier name to canonical_name
    3. Save updated cells_list.json
    """

    for juris_dir in sorted(COUNTRIES_DIR.iterdir()):
        if not juris_dir.is_dir():
            continue
        if jurisdictions and juris_dir.name not in jurisdictions:
            continue

        l3_dir = juris_dir / "level_3"
        l2_dir = juris_dir / "level_2"
        if not l3_dir.exists() or not l2_dir.exists():
            continue

        for venue_dir in sorted(l3_dir.iterdir()):
            if not venue_dir.is_dir() or venue_dir.name.startswith("_"):
                continue

            par_raw = venue_dir / "_parallel_raw"
            if not par_raw.exists():
                continue

            venue_key = venue_dir.name

            # Load cells_list
            cells_list_path = l2_dir / venue_key / "cells_list.json"
            if not cells_list_path.exists():
                continue
            cells_data = _load_json(cells_list_path)
            if not cells_data:
                continue
            cells = cells_data.get("cells", [])

            # Load all tier_maps for this venue
            tier_maps: dict[str, dict] = {}  # instrument_class -> tier_map data
            for tm_file in sorted(par_raw.glob("*_tier_map.json")):
                tm = _load_json(tm_file)
                if not tm:
                    continue
                # Extract instrument_class from filename
                # Format: {venue_key}_{instrument_class}_tier_map.json
                stem = tm_file.stem
                ic = stem.replace(f"{venue_key}_", "", 1).replace("_tier_map", "")
                tier_maps[ic] = tm

            if not tier_maps:
                continue

            # Determine ISO code from existing cell_ids
            iso = ""
            for c in cells:
                cid = c.get("cell_id", "")
                parts = cid.split("_")
                if len(parts) >= 2 and len(parts[0]) == 2:
                    iso = parts[0]
                    break

            if not iso:
                logger.warning(
                    "Cannot determine ISO code for %s — skipping", venue_key
                )
                continue

            changed = False

            for ic, tm in tier_maps.items():
                canonical_tiers = [
                    t
                    for t in tm.get("tiers", [])
                    if t.get("belongs_to_venue", False)
                ]

                if not canonical_tiers:
                    continue

                # Find existing cells for this instrument_class
                ic_cells = [c for c in cells if c.get("instrument_class") == ic]

                # Identify flat cells (outdated tier names)
                flat_cells = [
                    c
                    for c in ic_cells
                    if c.get("tier", "").startswith("(no listing")
                ]

                if len(canonical_tiers) == 1 and flat_cells:
                    # Single canonical tier, flat cell — just update tier name
                    flat_cells[0]["tier"] = canonical_tiers[0]["canonical_name"]
                    changed = True
                    logger.info(
                        "[UPDATED] %s/%s: flat -> %s",
                        venue_key,
                        ic,
                        canonical_tiers[0]["canonical_name"],
                    )
                    continue

                if len(canonical_tiers) > 1 and flat_cells:
                    # Multiple tiers found but cells_list has flat cell(s)
                    # Reuse first flat cell, create new cells for rest
                    first = True
                    for ct in canonical_tiers:
                        canon_id = ct["canonical_id"]
                        canon_name = ct["canonical_name"]

                        if first and flat_cells:
                            # Reuse the existing flat cell (preserves cell_dir)
                            flat_cells[0]["tier"] = canon_name
                            changed = True
                            logger.info(
                                "[UPDATED] %s/%s: flat -> %s (reused existing cell)",
                                venue_key,
                                ic,
                                canon_name,
                            )
                            first = False
                        else:
                            # Build new cell_id
                            slug = (
                                canon_id.replace(" ", "_")
                                .replace("-", "_")[:40]
                            )
                            new_cell_id = f"{iso}_{venue_key}_{slug}_{ic}"

                            # Skip if already exists
                            if any(
                                c.get("cell_id") == new_cell_id for c in cells
                            ):
                                logger.info(
                                    "[SKIP] %s/%s: cell %s already exists",
                                    venue_key,
                                    ic,
                                    new_cell_id,
                                )
                                continue

                            # Clone structure from first flat cell as template
                            template = flat_cells[0]
                            new_cell = {
                                "cell_id": new_cell_id,
                                "venue_key": venue_key,
                                "tier": canon_name,
                                "instrument_class": ic,
                                "secondary_admission_applicable": template.get(
                                    "secondary_admission_applicable", False
                                ),
                                "distinct_regime": template.get(
                                    "distinct_regime", False
                                ),
                                "legacy": template.get("legacy", False),
                                "admission_path": template.get(
                                    "admission_path"
                                ),
                                "segment": template.get("segment"),
                                "modifiers": template.get("modifiers", []),
                                "prompts": {},
                            }
                            cells.append(new_cell)
                            changed = True
                            logger.info(
                                "[CREATED] %s/%s: new cell %s (tier: %s)",
                                venue_key,
                                ic,
                                new_cell_id,
                                canon_name,
                            )

                            # Create cell directory in L3
                            cell_dir = venue_dir / new_cell_id
                            cell_dir.mkdir(parents=True, exist_ok=True)
                    continue

                # Non-flat cells — check if all canonical tiers have matches
                for ct in canonical_tiers:
                    canon_name = ct["canonical_name"]
                    matched = False
                    for c in ic_cells:
                        cell_tier = c.get("tier", "")
                        if cell_tier.lower() == canon_name.lower():
                            matched = True
                            break
                        if (
                            canon_name.lower() in cell_tier.lower()
                            or cell_tier.lower() in canon_name.lower()
                        ):
                            matched = True
                            break
                    if not matched:
                        logger.warning(
                            "[UNMATCHED] %s/%s: canonical tier '%s' has no matching cell",
                            venue_key,
                            ic,
                            canon_name,
                        )

            if changed:
                cells_data["cells"] = cells
                _save_json(cells_list_path, cells_data)
                logger.info("[SAVED] cells_list.json for %s", venue_key)


def run_canonical_tier_mapping(
    llm=None,
    jurisdictions: Optional[list[str]] = None,
) -> dict:
    """
    For each venue x instrument_class in _parallel_raw, run LLM canonical mapping.
    Returns dict of {(venue_key, instrument_class): TierCanonicalMap}.

    Saves results to _parallel_raw/{venue}_{ic}_tier_map.json for each mapping.
    """
    groups = _discover_groups(jurisdictions=jurisdictions)
    if not groups:
        logger.info("No venue x instrument_class groups found to map.")
        return {}

    # Filter out already-mapped groups (idempotent)
    pending = []
    for g in groups:
        out_path = g["raw_dir"] / f"{g['venue_key']}_{g['instrument_class']}_tier_map.json"
        if out_path.exists():
            logger.info(
                "Skip (already mapped): %s / %s / %s",
                g["jurisdiction_ru"], g["venue_key"], g["instrument_class"],
            )
            continue
        pending.append(g)

    if not pending:
        logger.info("All groups already mapped. Nothing to do.")
        return {}

    logger.info("Found %d groups to map (out of %d total).", len(pending), len(groups))

    # Build LLM if not provided
    if llm is None:
        llm = ChatOpenAI(
            model=LLM_SMART_MODEL,
            api_key=os.environ["OPENAI_API_KEY"],
            temperature=0,
        )

    chain = llm.with_structured_output(TierCanonicalMap)

    # Prepare batch inputs
    batch_inputs = []
    for g in pending:
        # Load raw files
        tiers_by_qt: dict[str, list[dict]] = {}
        for qt in ("3A", "3B", "3C"):
            fpath = g["files"].get(qt)
            if fpath and fpath.exists():
                raw = _load_json(fpath) or {}
                content = raw.get("content", {})
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        content = {}
                tiers_by_qt[qt] = content.get("tiers", [])
            else:
                tiers_by_qt[qt] = []

        # Load venue card
        venue_card = _load_venue_card(g["jurisdiction_ru"], g["venue_key"])

        # Build user prompt
        user_prompt = _build_tier_mapping_prompt(
            venue_card=venue_card,
            tiers_3a=tiers_by_qt.get("3A", []),
            tiers_3b=tiers_by_qt.get("3B", []),
            tiers_3c=tiers_by_qt.get("3C", []),
            instrument_class=g["instrument_class"],
        )

        batch_inputs.append([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])

    # Run LLM batch
    logger.info("Running LLM batch with %d prompts...", len(batch_inputs))
    results = chain.batch(
        batch_inputs,
        config={"max_concurrency": 50},
        return_exceptions=True,
    )

    # Save results
    output_map = {}
    success_count = 0
    error_count = 0

    for g, result in zip(pending, results):
        out_path = g["raw_dir"] / f"{g['venue_key']}_{g['instrument_class']}_tier_map.json"

        if isinstance(result, Exception):
            logger.error(
                "LLM error for %s / %s / %s: %s",
                g["jurisdiction_ru"], g["venue_key"], g["instrument_class"],
                str(result),
            )
            error_count += 1
            continue

        # Convert Pydantic model to dict
        try:
            data = result.model_dump()
        except AttributeError:
            data = result.dict()

        _save_json(out_path, data)

        key = (g["venue_key"], g["instrument_class"])
        output_map[key] = result
        success_count += 1

        tier_count = len(data.get("tiers", []))
        belongs_count = sum(1 for t in data.get("tiers", []) if t.get("belongs_to_venue"))
        logger.info(
            "Mapped %s / %s / %s: %d tiers (%d belong to venue)",
            g["jurisdiction_ru"], g["venue_key"], g["instrument_class"],
            tier_count, belongs_count,
        )

    logger.info(
        "Tier mapping complete: %d success, %d errors out of %d total.",
        success_count, error_count, len(pending),
    )

    return output_map
