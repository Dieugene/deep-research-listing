"""
Level 2: LLM postprocessing — builds venue_card.json, cells_list.json,
and Level 3 prompts for each pilot venue.

Steps per venue:
  1. Read 2A_structure.json
  2. LLM (gpt-5) with_structured_output → VenueCard → venue_card.json
  3. Derive cells from VenueCard.instrument_coverage → cells_list.json
  4. LLM (gpt-5) generates prompts 3A/3B/3C per cell (legacy cells: 3A only)

Usage:
    python -m level_2.postprocess             # process all pilot venues
    python -m level_2.postprocess --venue LSE_Main_Market # process one venue
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
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
    PILOT_VENUES,
    PROMPTS_LEVEL3_DIR,
    get_country_level1_dir,
    get_country_level2_dir,
)
from pipeline.storage import load_json, save_json, save_prompt
from pipeline.logging_setup import get_logger
from pipeline.config import LEVEL2_LOG_FILE
from level_3.cell_runner import SCHEMAS as L3_SCHEMAS

logger = get_logger("postprocess_l2", LEVEL2_LOG_FILE)

PARALLEL_MAX_CHARS = 18000      # суммарный лимит task_spec + input
PARALLEL_SCHEMA_OVERHEAD = 200  # запас на JSON-обёртку {"type":"json","json_schema":{...}}
MAX_COMPRESSION_ATTEMPTS = 3


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class InstrumentCoverage(BaseModel):
    """
    One entry per instrument admission path for the venue.
    Populated from Question B of the LLM extraction prompt.
    Cells are generated from InstrumentCoverage, NOT from TierDef.
    """
    instrument_class: str  # only from: equity, bond, fund, depositary_receipt
    regime_name: Optional[str] = None   # non-null for distinct_regime and legacy entries (used as cell label)
    regime_name_ru: Optional[str] = None
    distinct_regime: bool = False       # Case 2: fundamentally different secondary regime → separate cell
    admission_path: Optional[str] = None  # "trading_only" if admission to trading without official listing
    secondary_admission_applicable: bool = False  # Case 1: same regime, reduced thresholds → flag only
    legacy: bool = False                # grandfathering/transition category → limited L3
    segment: Optional[str] = None   # non-null if this entry is for a specific thematic segment with own admission criteria
    modifiers: list[str] = []           # admission regime modifiers (shell_company, spac, wvr, etc.)
    notes: Optional[str] = None


class TierDef(BaseModel):
    """
    Describes the structural hierarchy of a venue (listing tiers and thematic segments).
    From Question A of the LLM extraction prompt.
    Does NOT generate cells — cells come from InstrumentCoverage.
    """
    tier_name: str
    tier_name_ru: str
    segment_type: str  # "listing_tier" | "thematic_segment" | "board"
    rulebook_chapters: Optional[dict[str, str]] = None  # instrument_class -> chapter reference (informational)


class SegmentDef(BaseModel):
    """
    A thematic or sectoral segment within a venue (metadata only).
    From Question A (Part A2) of the LLM extraction prompt.
    generates_cell=True if the segment has own admission criteria that differ
    from the base venue requirements — in that case a corresponding
    InstrumentCoverage entry (with segment field set) must also be present.
    """
    segment_name: str
    segment_name_ru: str
    generates_cell: bool = False
    rulebook_chapters: Optional[dict[str, str]] = None


class RegimeModifier(BaseModel):
    modifier_name: str
    modifier_description: str
    applicable_issuer_types: list[str]


class VenueCard(BaseModel):
    venue_key: str
    venue_name_english: str
    venue_name_local: str
    venue_name_ru: str
    jurisdiction: str
    jurisdiction_ru: str
    venue_type: str  # regulated_market | MTF | OTF | other
    operator: str
    issuer_eligibility_separate: bool
    issuer_eligibility_authority: str  # "exchange" | "regulator" | "both"
    issuer_eligibility_legal_basis: str  # specific chapter/rule reference, or "not found"
    secondary_listing_regime: bool
    secondary_listing_description: Optional[str] = None
    listing_architecture: Optional[str] = None  # "trading_only" for MTF/OTF venues where official listing is not applicable
    tiers: list[TierDef] = []  # from Question A: listing tiers and thematic segments (structure only)
    segments: list[SegmentDef] = []  # from Question A Part A2: thematic/sectoral segments
    instrument_coverage: list[InstrumentCoverage] = []  # from Question B: generates cells
    regime_modifiers: list[RegimeModifier] = []
    key_rulebook_references: str
    notes: str
    notes_ru: str


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def _get_llm(model: str = LLM_SMART_MODEL) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        api_key=os.environ["OPENAI_API_KEY"],
        temperature=0,
        request_timeout=120,
    )


def _build_venue_prompt(
    venue: dict,
    raw_2a: dict,
    jurisdiction_card: dict,
) -> str:
    """Build the VenueCard extraction prompt string (no LLM call)."""
    raw_json = json.dumps(raw_2a, ensure_ascii=False, indent=2)
    card_json = json.dumps(jurisdiction_card, ensure_ascii=False, indent=2)

    return f"""You are processing Deep Research results about a securities exchange.
This prompt is fully self-contained — all necessary context is provided below.

JURISDICTION CONTEXT (Level 1 card):
{card_json}

VENUE BEING PROCESSED:
venue_key: {venue["venue_key"]}
venue_name_english: {venue["venue_name_english"]}
venue_name_local: {venue["venue_name_local"]}
jurisdiction (English): {venue["name_en"]}
jurisdiction (Russian): {venue["name_ru"]}

RAW DEEP RESEARCH OUTPUT (2A):
{raw_json}

CRITICAL RULE — Instrument-class chapters are NOT tiers and NOT segments.
If a venue organizes its rulebook into chapters by instrument type (e.g., one
chapter for equities, one for debt, one for funds), these chapters are NOT
listing tiers and NOT segments. They define which instrument classes are
available and will be used to generate Level 3 research cells.

Report them in response to QUESTION B (instrument class coverage), NOT in
response to QUESTION A (tier/segment structure).

A listing tier is a hierarchy of STRICTNESS within the SAME instrument class.
If the venue has no such hierarchy — report tiers as empty (no listing tiers).

DEFINITION — Listing Tier (DEF-A05):
A hierarchical level within a single venue that determines the strictness of
admission and continuing obligation requirements. Higher tiers impose stricter
requirements and signal higher quality to investors.
A tier creates a VERTICAL hierarchy: stricter vs. less strict. An issuer "qualifies"
for a higher tier by meeting more demanding thresholds for the SAME instrument class.

DEFINITION — Specialized Segment (DEF-A04):
A thematic or sectoral subdivision within a venue, with ADDITIONAL criteria on top
of the venue's base requirements. A segment does NOT replace base requirements — it
adds to them. A segment creates a HORIZONTAL grouping: thematic or sectoral (industry,
ESG, company size, innovation focus).

RULE — Segment cell generation:
A specialized segment generates a Level 3 cell ONLY IF it has its own admission
requirements that DIFFER from the base venue requirements (separate rulebook chapter
or substantially different eligibility criteria).
If the segment is purely informational (marketing label, index membership,
disclosure overlay with no distinct admission criteria) — it does NOT generate a cell;
record it in segments[] with generates_cell=false.
If a segment DOES generate a cell: record it in segments[] with generates_cell=true,
AND create a corresponding InstrumentCoverage entry with segment set to the segment
abbreviation/name and the relevant instrument_class.

EXAMPLES — generates_cell:

generates_cell = TRUE:
- LSE Main Market → Specialist Fund Segment (SFS): has its own admission
  criteria under UKLR Chapter 11 / ADS Schedule 4, different eligibility
  requirements from standard ESCC or CEF categories. → generates_cell = true.

generates_cell = FALSE:
- LSE Main Market → High Growth Segment (HGS): marketing label for companies
  meeting certain growth criteria. No separate admission procedure — companies
  apply through standard ESCC admission and receive HGS designation post-admission.
  → generates_cell = false.
- LSE Main Market → Shanghai-London Stock Connect: cross-border access arrangement.
  Admission is governed by the standard rules of each exchange, not by separate
  Stock Connect admission criteria. → generates_cell = false.
- LSE Main Market → Sustainable Bond Market (SBM): disclosure overlay — issuer
  commits to additional ESG reporting but admission criteria are the same as
  standard bond admission. → generates_cell = false.

KEY TEST: Does an issuer need to meet DIFFERENT admission criteria to enter
this segment, compared to the base venue requirements? If the only difference
is post-admission obligations (extra reporting, extra disclosure, marketing
designation) — generates_cell = false. If the admission criteria themselves
differ — generates_cell = true.

DEFINITION — Admission Regime Modifier (DEF-G08):
A set of rule modifications for a specific TYPE OF ISSUER (biotech, SPAC, WVR,
shell companies) within the same instrument class. The issuer remains listed on the
same venue; only certain rules are adjusted.

CLASSIFICATION RULE — Modifier vs. instrument class:
If a separate chapter/category of the rulebook applies to a specific TYPE OF ISSUER
(e.g., shell companies, SPACs, biotech without revenue) while the INSTRUMENT CLASS
remains the same (equities) — classify this as an admission regime modifier (DEF-G08),
NOT as a separate instrument class.
Record modifiers in the `modifiers` field of the relevant InstrumentCoverage entry,
NOT as separate entries.
Example: "Equity Shares – Shell Companies" → instrument class = equity, modifier = shell_company.

DEFINITION — Secondary Admission (DEF-G06):
Admission of an instrument already listed on another venue.

TWO CASES:

CASE 1 — MODIFIED PRIMARY REGIME: Same admission regime as primary, but with
reduced thresholds or exemptions. Structure is the same; only values differ.
→ Record as secondary_admission_applicable=true on the PRIMARY instrument class entry.
→ Do NOT create a separate entry.
→ Add a note listing which thresholds are reduced.

CASE 2 — DISTINCT SECONDARY REGIME: Separate set of rules with fundamentally
different structure — different eligibility criteria (e.g., requirement for primary
listing in a "recognized jurisdiction"), equivalence-based assessment, or substantially
different procedures.
→ Record as a SEPARATE InstrumentCoverage entry with distinct_regime=true.
→ Set regime_name to the official name of this secondary regime.

TEST: Can the secondary admission requirements be described as "same as primary,
except [list of reduced thresholds]"? If yes → Case 1 (flag). If requirements have
fundamentally different STRUCTURE → Case 2 (separate entry).

IMPORTANT: The DEF-G06 Case 2 test applies not only to secondary listing regimes
but also to distinct sub-categories WITHIN an instrument class.
If a venue has two types of bond admission that differ in fundamental structure
(e.g., professional-only debt under a streamlined regime without prospectus vs. retail
debt with full prospectus requirements and different disclosure standards), apply the
Case 2 test: "Can the retail requirements be described as 'same as professional, except
[list]'?" If NO (different structure, different target audience, different disclosure
regime) → create TWO separate InstrumentCoverage entries with distinct regime_names,
NOT modifiers.

DEFINITION — Listing/Admission Architecture (DEF-G04):
In some jurisdictions, "official listing" (inclusion in an official register
maintained by a listing authority) and "admission to trading" (permission to
trade on a venue) are TWO SEPARATE legal acts, performed by different bodies,
under different rules. In other jurisdictions, these are merged into a single
process.

VALUES:
- "merged" — listing and admission to trading are a single procedure,
  single decision-maker. Most jurisdictions.
- "split" — listing and admission are separate. An instrument can be admitted
  to trading without being officially listed. Example: UK (FCA Official List
  vs. LSE admission to trading under ADS).

QUESTION — Venue listing architecture:
Set VenueCard.listing_architecture:
- If this venue is an MTF or OTF (where official listing is not applicable at all,
  and the venue only admits instruments to trading): set listing_architecture = "trading_only"
  and leave admission_path = null on ALL cells for this venue.
- If the jurisdiction has "split" architecture and this venue requires official listing
  (regulated market): set listing_architecture = "split".
- If listing and admission are merged: set listing_architecture = "merged".

IMPORTANT DISTINCTION:
- VenueCard.listing_architecture = "trading_only" → the ENTIRE venue operates without
  official listing (all cells on this venue). Example: AIM (MTF).
- InstrumentCoverage.admission_path = "trading_only" → used ONLY when the venue is
  "split" AND a specific admission path exists that bypasses the official listing for
  certain instruments. Example: ADS Schedule 6 on LSE Main Market.

Do NOT set admission_path = "trading_only" on cells of an MTF/OTF venue. That is
redundant and creates false analogy with "split" venues.

QUESTION — Admission to trading without official listing (for "split" venues only):
If this venue operates in a jurisdiction where official listing and admission
to trading are SEPARATE legal acts ("split" architecture per DEF-G04):
does this venue admit instruments to TRADING ONLY for certain specific instrument
classes, without inclusion on the official list?

If yes — this is a SEPARATE ADMISSION PATH with its own set of rules
(different rulebook, different authority, different procedure).
→ Record it as a SEPARATE InstrumentCoverage entry with:
   - admission_path = "trading_only"
   - distinct_regime = false (this is NOT a secondary listing per DEF-G06)
   - regime_name = official name of this path (e.g., "Admission to Trading Only (ATT Only)")
   - instrument_class = the relevant instrument class

KEY DISTINCTION:
- distinct_regime (DEF-G06 Case 2) = secondary LISTING with fundamentally different rules
- admission_path = "trading_only" = admission to TRADING without any listing at all
These are different concepts. Do NOT use distinct_regime=true for trading-only paths.

If the jurisdiction has "merged" architecture or venue_type is MTF/OTF — skip this question.

QUESTION — Legacy categories:
Are there any listing categories, tiers, or segments CLOSED to new admissions?
(grandfathering/transition categories where existing issuers remain but no new
admissions are accepted)
→ Record as a SEPARATE InstrumentCoverage entry with legacy=true.
→ Set regime_name to the official name of the legacy category.
→ L3 research will be limited to continuing obligations and delisting procedures only.

Your tasks:

QUESTION A — Venue structure:

Part A1: Populate `tiers[]` (TierDef schema) — vertical hierarchy only:
- Listing tiers: hierarchical levels within a venue for the SAME instrument class
  (vertical hierarchy of strictness). If no tiers → empty list.
- Board subdivisions (where one venue has multiple named boards, e.g., Main Board vs. GEM
  at different legal entities — do NOT include here; they are separate venues).
- Do NOT put instrument-class chapters here.
- Do NOT put secondary regimes here.
- Do NOT put legacy categories here.
- Do NOT put modifiers here.
- Do NOT put thematic segments here (they go in Part A2).

Part A2: Populate `segments[]` (SegmentDef schema) — thematic/sectoral subdivisions:
- Thematic or sectoral segments with ADDITIONAL criteria on top of base requirements.
- Set generates_cell=true ONLY if the segment has own admission requirements that
  differ from the base venue requirements (per the RULE above).
- Set generates_cell=false for purely informational labels (marketing labels, index
  membership, disclosure overlays with no distinct admission criteria).

QUESTION B — Instrument class coverage (populate `instrument_coverage` field):
For each instrument class admitted to this venue, create one InstrumentCoverage entry:
- Set instrument_class from: ["equity", "bond", "fund", "depositary_receipt"]
- Set modifiers[] if any admission regime modifiers apply to this class
- If Case 1 secondary applies: set secondary_admission_applicable=true on this entry
- If Case 2 distinct secondary regime exists: create a SEPARATE additional entry with
  distinct_regime=true and regime_name = official name of that regime
- If a legacy/transition category exists for this instrument class: create a SEPARATE
  entry with legacy=true and regime_name = official name of that category
- For segments that generate cells (generates_cell=true in segments[]): create a SEPARATE
  InstrumentCoverage entry with segment = segment abbreviation/name and instrument_class =
  the instrument class that this segment covers
- For bond instrument classes: check whether different sub-categories of bonds (e.g.,
  professional-only vs. retail bonds) have fundamentally different admission structures.
  Apply DEF-G06 Case 2 test. If the structures differ → separate InstrumentCoverage entries
  with distinct regime_names, NOT modifiers.
- A venue with equities that also has: a shell_company modifier, a distinct secondary
  regime, and a legacy transition category → 3 entries for "equity" total:
  (1) base equity with modifiers=["shell_company"]
  (2) distinct_regime equity with regime_name="[secondary regime name]"
  (3) legacy equity with regime_name="[transition category name]"

Additional tasks:
- venue_type: "regulated_market", "MTF", "OTF", or "other"
- For venue_type, secondary_listing_regime, issuer_eligibility_separate,
  issuer_eligibility_authority, issuer_eligibility_legal_basis: follow current rules.
- issuer_eligibility_authority: exactly one of "exchange", "regulator", "both"
- issuer_eligibility_legal_basis: specific legal chapter/rule; "not found" if unknown.
  Do NOT describe specific requirements here — only architectural fact and legal basis.
- regime_modifiers (DEF-G08): identify all modifiers in regime_modifiers[] field.
  These are NOT tiers or segments.
- Translate venue_name_ru, notes_ru to Russian.
- key_rulebook_references: cite main rulebook documents.

VALIDATION before finalizing instrument_coverage:
(a) Does each entry have exactly one instrument_class from the allowed list?
(b) Are modifiers properly listed in modifiers[] rather than as separate entries?
(c) Is each distinct secondary regime a truly separate entry (distinct_regime=true)?
(d) Is each legacy category a separate entry (legacy=true)?
(e) If venue_type is MTF or OTF: are all cells free of admission_path="trading_only"
    (it should be on VenueCard.listing_architecture instead)?
(f) For bond coverage: do different bond admission regimes (professional vs. retail)
    have fundamentally different structures? If yes → separate entries.
(g) For segments with generates_cell=true: is there a matching InstrumentCoverage
    entry with segment field set?

Return valid JSON matching the required schema. All fields must be populated.
"""


def _build_venue_card(
    venue: dict,
    raw_2a: dict,
    jurisdiction_card: dict,
) -> VenueCard:
    """Call LLM to extract a structured VenueCard from raw 2A research (single-venue)."""
    prompt = _build_venue_prompt(venue, raw_2a, jurisdiction_card)
    logger.info("Building VenueCard for %s via LLM...", venue["venue_key"])
    llm = _get_llm()
    chain = llm.with_structured_output(VenueCard, method="function_calling")
    card: VenueCard = chain.invoke(prompt)
    logger.info("VenueCard built for %s (%d coverage entries)", venue["venue_key"], len(card.instrument_coverage))
    return card


# ---------------------------------------------------------------------------
# cell_id helpers
# ---------------------------------------------------------------------------

def _tier_slug(tier_name: str, max_len: int = 30) -> str:
    """
    Convert tier name to snake_case slug, max max_len chars.
    If the name contains a parenthetical acronym like (ESCC), prefer it as the slug.
    """
    # Check for a parenthetical acronym: e.g., "Equity Shares – Commercial Companies (ESCC)"
    acronym_match = re.search(r"\(([A-Z0-9]{2,10})\)", tier_name)
    if acronym_match:
        return acronym_match.group(1).lower()

    # Otherwise build snake_case from ALL words (including parenthetical content)
    slug = re.sub(r"[^a-zA-Z0-9\s]", "", tier_name)  # keep only alphanumeric and spaces
    slug = "_".join(slug.split()).lower()
    return slug[:max_len].rstrip("_")


def _iso_country_code(name_en: str) -> str:
    mapping = {
        "United Kingdom": "GB",
        "Hong Kong": "HK",
        "Russia": "RU",
    }
    return mapping.get(name_en, name_en[:2].upper())


def _make_cell_id(iso: str, venue_key: str, tier_name: str, instrument_class: str) -> str:
    slug = _tier_slug(tier_name)
    return f"{iso}_{venue_key}_{slug}_{instrument_class}"


# ---------------------------------------------------------------------------
# Level 3 prompt generation
# ---------------------------------------------------------------------------

PROMPT_3A_META = """You are preparing a Deep Research query for a securities exchange cell.
This prompt is fully self-contained — all context is included below.

VENUE: {venue_name_english} ({venue_name_local})
VENUE TYPE: {market_type}
OPERATOR: {operator_name}
JURISDICTION: {jurisdiction_en} (regulator: {regulator_name})
TIER: {tier_name}
TIER TYPE: {segment_type}
INSTRUMENT CLASS: {instrument_class}
RULEBOOK CHAPTERS for this tier/class: {rulebook_chapters}
KEY RULEBOOK REFERENCES: {key_rulebook_references}
ADMISSION ARCHITECTURE: {admission_architecture}

CONTEXT: {venue_name_english} is a {market_type} operated by {operator_name}.
{tier_name} is a {segment_type} within this venue.
This query covers {instrument_class} instruments on this specific venue/tier.

DEFINITIONS to include verbatim in the generated prompt:

DEFINITION — Admission Regime:
The specific combination of rules, procedures, and requirements that apply to a
particular admission case. An admission regime is determined by three coordinates:
venue × listing tier (if any) × instrument class/subclass.

Each unique combination of these three coordinates potentially has its own regime
and constitutes a separate "cell" for research purposes.

WHEN TO CREATE A SEPARATE CELL: If changing any one of the three coordinates changes
the set of applicable admission rules — that is a separate cell. If two instrument
subclasses share identical admission rules on the same venue and tier — they can be
merged into one cell with a note.

DEFINITION — Separation of Issuer and Instrument Requirements:
Within any admission regime, requirements fall into two categories:
- ISSUER requirements: conditions on the issuer as an entity (financial history,
  profitability, corporate governance, board composition, auditor standards).
- INSTRUMENT requirements: conditions on the specific security being admitted
  (free float, minimum shares outstanding, price, distribution among holders).

This is an ANALYTICAL distinction that applies to ALL jurisdictions. However,
jurisdictions differ in an ARCHITECTURAL fact: whether the issuer is admitted
separately from its instruments.

WHAT TO RECORD:
(1) ARCHITECTURAL FACT: Does this venue admit the issuer separately (issuer
    "eligibility" as a one-time process, after which individual issues are admitted
    via simplified procedure)? Or is there a single admission procedure where both
    issuer and instrument requirements are checked together?
(2) SPECIFIC REQUIREMENTS: Regardless of the architecture, list requirements in
    two groups — those applying to the issuer and those applying to the instrument.

Generate a Deep Research prompt in English for query 3A: PRIMARY ADMISSION.

The prompt must request research organized into these thematic blocks:
1. ADMISSION OVERVIEW — general description of the admission regime, main paths and tests available.
2. ELIGIBILITY REQUIREMENTS — issuer-level requirements: financial history, profitability, assets,
   corporate governance, auditor standards, alternative eligibility paths.
3. INSTRUMENT REQUIREMENTS — security-level requirements: free float, market capitalisation,
   minimum shareholders, minimum share price, issue size, and linkages between these.
4. SPONSOR AND INFRASTRUCTURE — sponsor/nomad/listing agent requirements, prospectus/offering
   document requirements, their role in the process.
5. RESTRICTIONS AND LOCK-UPS — lock-up periods, escrow requirements, restrictions post-admission.
6. PROCEDURE AND TIMELINE — application process, submission requirements, review stages,
   decision-making, timeline, appeal mechanisms.
7. DISCLOSURE AT ADMISSION — prospectus/listing document content requirements, key disclosure items.
8. SPECIAL REGIMES — modifications for specific issuer types: SPAC, WVR, biotech, foreign issuers,
   and any other special admission tracks relevant to this tier/class.
9. ADDITIONAL FINDINGS — any relevant requirements not covered by the blocks above.

For EVERY specific requirement, threshold, or condition found, the prompt must ask for:
- What exactly is established (value, unit, formula)
- How it is calculated (what is included/excluded)
- Whether alternatives exist (either/or paths, alternative tests)
- Whether it varies by company size, type, or other factors
- Whether it is linked to other requirements

The prompt must instruct: "Do not just state the headline figure — explain the full construction
of each requirement. Cite specific rule/provision numbers for every item."

Use the exact rulebook chapter references above in the prompt.
Be self-contained — include venue name, tier name, instrument class, and regulator name
within the prompt itself.

Return ONLY the generated Deep Research prompt text, nothing else.
{secondary_case1_block}{modifiers_note}{legacy_note}
"""

PROMPT_3B_META = """You are preparing a Deep Research query for a securities exchange cell.
This prompt is fully self-contained — all context is included below.

VENUE: {venue_name_english} ({venue_name_local})
VENUE TYPE: {market_type}
OPERATOR: {operator_name}
JURISDICTION: {jurisdiction_en} (regulator: {regulator_name})
TIER: {tier_name}
TIER TYPE: {segment_type}
INSTRUMENT CLASS: {instrument_class}
RULEBOOK CHAPTERS for this tier/class: {rulebook_chapters}
KEY RULEBOOK REFERENCES: {key_rulebook_references}

CONTEXT: {venue_name_english} is a {market_type} operated by {operator_name}.
{tier_name} is a {segment_type} within this venue.
This query covers {instrument_class} instruments on this specific venue/tier.

Generate a Deep Research prompt in English for query 3B: CONTINUING OBLIGATIONS,
SUSPENSION and DELISTING (negative aspects).

The prompt must cover:
1. Continuing obligations: quantitative thresholds that must be maintained (and how
   they differ from initial admission requirements), qualitative ongoing obligations,
   periodic reporting requirements (deadlines, formats, accounting standards),
   compliance confirmation procedures.
2. Suspension: grounds for suspension, procedure, disclosure obligations, duration limits.
3. Compulsory delisting: grounds, procedure, grace periods, shareholder protections,
   disclosure.
4. Voluntary delisting: conditions, procedure, shareholder approval requirements.
5. Local terminology for delisting and suspension in official language.

Use the exact rulebook chapter references above. Ask for specific rule/provision numbers.
Be self-contained — include venue name, tier, instrument class, and regulator name.

IMPORTANT: Focus specifically on these negative aspects — this is a separate targeted query
because these topics are often under-researched. Do NOT cover initial admission requirements.

Return ONLY the generated Deep Research prompt text, nothing else.
"""

PROMPT_3C_META = """You are preparing a Deep Research query for a securities exchange cell.
This prompt is fully self-contained — all context is included below.

VENUE: {venue_name_english} ({venue_name_local})
VENUE TYPE: {market_type}
OPERATOR: {operator_name}
JURISDICTION: {jurisdiction_en} (regulator: {regulator_name})
TIER: {tier_name}
TIER TYPE: {segment_type}
INSTRUMENT CLASS: {instrument_class}
RULEBOOK CHAPTERS for this tier/class: {rulebook_chapters}
KEY RULEBOOK REFERENCES: {key_rulebook_references}

CONTEXT: {venue_name_english} is a {market_type} operated by {operator_name}.
{tier_name} is a {segment_type} within this venue.
This query covers {instrument_class} instruments on this specific venue/tier.

Generate a Deep Research prompt in English for query 3C: MONITORING AND ENFORCEMENT.

The prompt must cover:
1. Monitoring regime: which body is responsible (exchange, regulator, or both),
   monitoring mechanisms (routine reviews, automated surveillance, ad-hoc requests),
   role of sponsor/nomad in ongoing monitoring, issuer reporting obligations to
   the exchange beyond public disclosure.
2. Sanctions: exchange sanctions (warning, fine, demotion, suspension, delisting),
   regulator sanctions, disciplinary procedure (investigation, hearing, appeal),
   publication of enforcement actions (where and whether published).
3. Enforcement practice: recent examples (last 3-5 years), general enforcement approach
   (tolerant vs strict).

Use the exact rulebook chapter references above. Ask for specific rule/provision numbers.
Be self-contained — include venue name, tier, instrument class, and regulator name.

Return ONLY the generated Deep Research prompt text, nothing else.
"""


def _combined_size(prompt_text: str, schema: dict) -> int:
    """Return combined character count of prompt + serialized schema (as Parallel sees it)."""
    schema_str = json.dumps({"type": "json", "json_schema": schema})
    return len(prompt_text) + len(schema_str)


def _validate_and_compress_existing_prompts(
    batch_items: list,
    llm: Any,
) -> None:
    """
    Validate size of already-generated L3 prompts against Parallel limits.
    Compresses oversized prompts in-place (updates the prompt files on disk).
    batch_items: list of (meta_prompt, cell_id, qt, prompt_path)
    """
    from langchain_core.messages import AIMessage as _AIMessage

    oversized: list[tuple[int, str, dict, list, Path]] = []

    for i, (meta_prompt, cell_id, qt, prompt_path) in enumerate(batch_items):
        path = Path(prompt_path)
        if not path.exists():
            continue
        prompt_text = path.read_text(encoding="utf-8")
        schema = L3_SCHEMAS.get(qt, {})
        if _combined_size(prompt_text, schema) > PARALLEL_MAX_CHARS:
            size = _combined_size(prompt_text, schema)
            logger.warning(
                "Existing prompt %s/%s exceeds Parallel limit: %d chars (limit %d)",
                cell_id, qt, size, PARALLEL_MAX_CHARS,
            )
            history = [HumanMessage(content=meta_prompt)]
            # We don't have the original AIMessage, simulate with a minimal placeholder
            # by treating the existing prompt as the AI's last response
            history.append(_AIMessage(content=prompt_text))
            oversized.append((i, prompt_text, schema, history, path))

    if not oversized:
        logger.info("All existing prompts are within Parallel size limits.")
        return

    logger.info(
        "%d existing prompts exceed Parallel limit, compressing...",
        len(oversized),
    )

    compression_needed = oversized  # list of (idx, prompt_text, schema, history, path)

    for attempt in range(1, MAX_COMPRESSION_ATTEMPTS + 1):
        if not compression_needed:
            break

        compression_inputs = []
        for idx, prompt_text, schema, history, path in compression_needed:
            schema_size = len(json.dumps({"type": "json", "json_schema": schema}))
            prompt_size = len(prompt_text)
            total = prompt_size + schema_size
            target_prompt_len = PARALLEL_MAX_CHARS - schema_size - PARALLEL_SCHEMA_OVERHEAD
            compress_msg = HumanMessage(content=(
                f"The prompt above is too long for the Parallel API. "
                f"Current sizes: prompt={prompt_size} chars, schema={schema_size} chars, "
                f"total={total} chars. Limit is {PARALLEL_MAX_CHARS} chars. "
                f"Please rewrite the prompt to approximately {target_prompt_len} characters. "
                f"Requirements: preserve ALL key questions, requirements, and context; "
                f"shorten by removing redundant phrasing, condensing examples, or shortening "
                f"explanatory text; do NOT remove entire sections or questions; "
                f"output only the compressed prompt text, nothing else."
            ))
            compression_inputs.append(history + [compress_msg])

        logger.info(
            "Compression attempt %d/%d: compressing %d prompts...",
            attempt, MAX_COMPRESSION_ATTEMPTS, len(compression_needed),
        )
        raw_compressed = llm.batch(
            compression_inputs,
            config={"max_concurrency": 50},
            return_exceptions=True,
        )

        still_oversized = []
        for ci, ((idx, prompt_text, schema, history, path), compressed_result) in enumerate(
            zip(compression_needed, raw_compressed)
        ):
            if isinstance(compressed_result, Exception):
                logger.warning(
                    "Compression attempt %d failed for %s: %s",
                    attempt, path.name, compressed_result,
                )
                still_oversized.append((idx, prompt_text, schema, history, path))
                continue

            new_text = compressed_result.content if hasattr(compressed_result, "content") else str(compressed_result)
            if _combined_size(new_text, schema) <= PARALLEL_MAX_CHARS:
                logger.info(
                    "Compression attempt %d succeeded for %s: %d -> %d chars",
                    attempt, path.name, len(prompt_text), len(new_text),
                )
                path.write_text(new_text, encoding="utf-8")
            else:
                logger.warning(
                    "Compression attempt %d: %s still oversized (%d chars), retrying...",
                    attempt, path.name, _combined_size(new_text, schema),
                )
                compress_msg_text = compression_inputs[ci][-1].content
                new_history = history + [HumanMessage(content=compress_msg_text), compressed_result]
                still_oversized.append((idx, new_text, schema, new_history, path))

        compression_needed = still_oversized

    if compression_needed:
        failed = [str(path) for _, _, _, _, path in compression_needed]
        logger.error(
            "PIPELINE STOP: %d prompts still exceed Parallel limit after %d compression attempts. "
            "Files: %s",
            len(compression_needed), MAX_COMPRESSION_ATTEMPTS, failed,
        )
        raise RuntimeError(
            f"Prompts too large after {MAX_COMPRESSION_ATTEMPTS} compression attempts: {failed}"
        )


def generate_all_level3_prompts(venues_data: list[dict]) -> None:
    """
    Generate Level 3 prompts for all cells across all venues in a single batch call.

    Each element of venues_data must have keys:
        venue, venue_card (VenueCard), raw_2a, cells (list of cell dicts),
        jurisdiction_card

    Idempotent: skips any prompt file that already exists on disk.
    Uses llm.batch() with max_concurrency=50 for parallel execution.
    """
    llm = _get_llm(LLM_FAST_MODEL)

    # ------------------------------------------------------------------
    # Build a flat list of (messages_str, save_path, cell_id, query_type)
    # ------------------------------------------------------------------
    batch_items: list[tuple[str, Path, str, str]] = []
    # all_items collects ALL prompts (new + existing) for post-generation validation
    all_items: list[tuple[str, str, str, Path]] = []  # (meta_prompt, cell_id, qt, path)

    for vd in venues_data:
        card: VenueCard = vd["venue_card"]
        jurisdiction_card: dict = vd["jurisdiction_card"]
        cells: list[dict] = vd["cells"]

        regulator_name = jurisdiction_card.get("regulator_name", "the local regulator")
        admission_architecture = jurisdiction_card.get("admission_architecture", "")

        for cell in cells:
            cell_id: str = cell["cell_id"]
            tier_name: str = cell["tier"]
            instrument_class: str = cell["instrument_class"]
            secondary_applicable: bool = cell.get("secondary_admission_applicable", False)
            distinct_regime: bool = cell.get("distinct_regime", False)
            is_legacy: bool = cell.get("legacy", False)
            modifiers: list = cell.get("modifiers", [])

            # segment_type is determined from cell flags (not from TierDef lookup)
            if is_legacy:
                segment_type = "legacy_transition"
            elif distinct_regime:
                segment_type = "distinct_secondary_regime"
            else:
                segment_type = "flat"

            # Case 1 secondary: secondary_applicable=True AND NOT distinct_regime
            is_case1_secondary = secondary_applicable and not distinct_regime

            # secondary_case1_block for 3A
            if is_case1_secondary:
                secondary_case1_block = (
                    "\nSECONDARY ADMISSION (CASE 1) NOTE: This venue also accepts secondary/dual listings "
                    "of this instrument class under a MODIFIED PRIMARY REGIME (same structure as primary, "
                    "with reduced thresholds or waivers). After block 8, add a 'SECONDARY ADMISSION' block "
                    "with sub-questions:\n"
                    "- Which specific quantitative thresholds are reduced for secondary-listed issuers "
                    "(vs. primary)? List each threshold and the modified value.\n"
                    "- Which requirements are waived entirely?\n"
                    "- What evidence of primary listing is required?\n"
                    "- Does the secondary regime have a different name or regulatory basis?"
                )
            else:
                secondary_case1_block = ""

            # modifiers_note for 3A
            if modifiers:
                modifiers_list = ", ".join(modifiers)
                modifiers_note = (
                    f"\nADMISSION REGIME MODIFIERS present on this cell: {modifiers_list}. "
                    "In block 8 (SPECIAL REGIMES), research how these modify the standard admission "
                    "requirements: which thresholds change, which requirements are adjusted or waived."
                )
            else:
                modifiers_note = ""

            # rulebook_chapters_str: TierDef no longer maps to instrument_classes;
            # use key_rulebook_references as fallback
            rulebook_chapters_str = "see key_rulebook_references above"

            # For legacy cells — only 3A with limited scope
            if is_legacy:
                query_types = [("3A", PROMPT_3A_META)]
                legacy_note = (
                    "\nLEGACY/TRANSITION CATEGORY NOTE: This category is closed to new admissions "
                    "(grandfathering/transition). SKIP blocks 1-7 (initial admission). Research ONLY:\n"
                    "- Continuing obligations for currently-listed issuers in this category\n"
                    "- Differences in continuing obligations vs. the main admission category\n"
                    "- Delisting or migration procedures: how are issuers expected to transition, "
                    "are there deadlines, what happens if they don't transition?\n"
                    "- Any special protections or obligations specific to this legacy category."
                )
            else:
                query_types = [
                    ("3A", PROMPT_3A_META),
                    ("3B", PROMPT_3B_META),
                    ("3C", PROMPT_3C_META),
                ]
                legacy_note = ""

            template_vars = dict(
                venue_name_english=card.venue_name_english,
                venue_name_local=card.venue_name_local,
                jurisdiction_en=card.jurisdiction,
                regulator_name=regulator_name,
                tier_name=tier_name,
                instrument_class=instrument_class,
                rulebook_chapters=rulebook_chapters_str,
                key_rulebook_references=card.key_rulebook_references,
                admission_architecture=admission_architecture,
                market_type=card.venue_type,
                operator_name=card.operator,
                segment_type=segment_type,
                secondary_case1_block=secondary_case1_block,
                modifiers_note=modifiers_note,
                legacy_note=legacy_note,
            )

            for query_type, meta_template in query_types:
                prompt_name = f"{cell_id}_{query_type}"
                save_path = PROMPTS_LEVEL3_DIR / f"{prompt_name}.txt"
                meta_prompt = meta_template.format(**template_vars)
                all_items.append((meta_prompt, cell_id, query_type, save_path))

                # Idempotency: skip if already generated
                if save_path.exists():
                    logger.debug("Skipping %s (already exists)", prompt_name)
                    # Ensure prompts dict on cell is updated
                    if "prompts" not in cell:
                        cell["prompts"] = {}
                    cell["prompts"][query_type] = str(save_path)
                    continue

                batch_items.append((meta_prompt, save_path, cell_id, query_type, cell))

    if not batch_items:
        logger.info("All Level 3 prompts already exist — nothing to batch.")
        _validate_and_compress_existing_prompts(all_items, llm)
        return

    logger.info(
        "Batching %d Level 3 prompt generation calls (max_concurrency=50)...",
        len(batch_items),
    )

    all_messages = [[HumanMessage(content=item[0])] for item in batch_items]
    remaining_messages = list(enumerate(all_messages))  # [(original_idx, messages), ...]
    results_map: dict[int, Any] = {}
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        if not remaining_messages:
            break
        inputs = [msg for _, msg in remaining_messages]
        raw = llm.batch(inputs, config={"max_concurrency": 20}, return_exceptions=True)
        still_failing = []
        for (orig_idx, msg), result in zip(remaining_messages, raw):
            if isinstance(result, Exception):
                logger.warning(
                    "L3 prompt generation: request %d failed on attempt %d: %s",
                    orig_idx, attempt, result,
                )
                still_failing.append((orig_idx, msg))
            else:
                results_map[orig_idx] = result
        remaining_messages = still_failing
        if still_failing and attempt < max_attempts:
            logger.info("Retrying %d failed requests (attempt %d/%d)...", len(still_failing), attempt + 1, max_attempts)

    if remaining_messages:
        failed_indices = [i for i, _ in remaining_messages]
        logger.error("L3 prompt generation: %d requests failed after %d attempts: indices %s", len(remaining_messages), max_attempts, failed_indices)

    # Reconstruct results in original order (None for permanently failed)
    results = [results_map.get(i) for i in range(len(all_messages))]

    # -----------------------------------------------------------------------
    # Compression pass: for prompts that exceed Parallel size limits
    # -----------------------------------------------------------------------
    # Build list of (batch_index, prompt_text, schema, conversation_history)
    # conversation_history = [HumanMessage(meta_prompt), AIMessage(generated_prompt)]
    compression_needed: list[tuple[int, str, dict, list]] = []
    for i, ((meta_prompt, save_path, cell_id, qt, cell), result) in enumerate(zip(batch_items, results)):
        if result is None:
            continue
        schema = L3_SCHEMAS.get(qt, {})
        prompt_text = result.content if hasattr(result, "content") else str(result)
        if _combined_size(prompt_text, schema) > PARALLEL_MAX_CHARS:
            history = [
                HumanMessage(content=meta_prompt),
                result,  # AIMessage from llm.batch
            ]
            compression_needed.append((i, prompt_text, schema, history))

    if compression_needed:
        logger.info(
            "%d prompts exceed Parallel size limit (%d chars), starting compression...",
            len(compression_needed), PARALLEL_MAX_CHARS,
        )

    for attempt in range(1, MAX_COMPRESSION_ATTEMPTS + 1):
        if not compression_needed:
            break

        # Build compression request messages for each oversized prompt
        compression_inputs = []
        for idx, prompt_text, schema, history in compression_needed:
            schema_size = len(json.dumps({"type": "json", "json_schema": schema}))
            prompt_size = len(prompt_text)
            total = prompt_size + schema_size
            target_prompt_len = PARALLEL_MAX_CHARS - schema_size - PARALLEL_SCHEMA_OVERHEAD
            compress_msg = HumanMessage(content=(
                f"The prompt above is too long for the Parallel API. "
                f"Current sizes: prompt={prompt_size} chars, schema={schema_size} chars, "
                f"total={total} chars. Limit is {PARALLEL_MAX_CHARS} chars. "
                f"Please rewrite the prompt to approximately {target_prompt_len} characters. "
                f"Requirements: preserve ALL key questions, requirements, and context; "
                f"shorten by removing redundant phrasing, condensing examples, or shortening "
                f"explanatory text; do NOT remove entire sections or questions; "
                f"output only the compressed prompt text, nothing else."
            ))
            compression_inputs.append(history + [compress_msg])

        logger.info(
            "Compression attempt %d/%d: compressing %d prompts...",
            attempt, MAX_COMPRESSION_ATTEMPTS, len(compression_needed),
        )
        raw_compressed = llm.batch(
            compression_inputs,
            config={"max_concurrency": 50},
            return_exceptions=True,
        )

        still_oversized = []
        for ci, ((idx, prompt_text, schema, history), compressed_result) in enumerate(zip(
            compression_needed, raw_compressed
        )):
            if isinstance(compressed_result, Exception):
                logger.warning(
                    "Compression attempt %d failed for batch index %d: %s",
                    attempt, idx, compressed_result,
                )
                still_oversized.append((idx, prompt_text, schema, history))
                continue

            new_text = compressed_result.content if hasattr(compressed_result, "content") else str(compressed_result)
            if _combined_size(new_text, schema) <= PARALLEL_MAX_CHARS:
                logger.info(
                    "Compression attempt %d succeeded for batch index %d: %d -> %d chars",
                    attempt, idx, len(prompt_text), len(new_text),
                )
                results[idx] = compressed_result  # replace in results with compressed version
            else:
                logger.warning(
                    "Compression attempt %d: batch index %d still oversized (%d chars), retrying...",
                    attempt, idx, _combined_size(new_text, schema),
                )
                # Correct history accumulation for next attempt:
                # history currently ends with [HM(meta), AM(original)] for attempt=1,
                # or [HM(meta), AM(orig), HM(compress_1), AM(compressed_1)] for attempt=2, etc.
                # We need to append the compress_msg that was sent and the compressed_result we got.
                compress_msg_text = compression_inputs[ci][-1].content
                new_history = history + [HumanMessage(content=compress_msg_text), compressed_result]
                still_oversized.append((idx, new_text, schema, new_history))

        compression_needed = still_oversized

    if compression_needed:
        failed_cells = [batch_items[i][2] for i, *_ in compression_needed]
        logger.error(
            "PIPELINE STOP: %d prompts still exceed Parallel limit after %d compression attempts. "
            "Affected cells: %s. Fix manually or adjust prompts, then re-run.",
            len(compression_needed), MAX_COMPRESSION_ATTEMPTS, failed_cells,
        )
        raise RuntimeError(
            f"Prompts too large after {MAX_COMPRESSION_ATTEMPTS} compression attempts: {failed_cells}"
        )

    for (meta_prompt, save_path, cell_id, query_type, cell), result in zip(
        batch_items, results
    ):
        if result is None:
            logger.warning("Skipping prompt for cell %s query %s — generation failed", cell_id, query_type)
            continue
        try:
            generated = result.content.strip()
            prompt_name = save_path.stem  # filename without .txt
            save_prompt(PROMPTS_LEVEL3_DIR, prompt_name, generated)
            if "prompts" not in cell:
                cell["prompts"] = {}
            cell["prompts"][query_type] = str(save_path)
            logger.debug("Saved %s_%s", cell_id, query_type)
        except Exception as e:
            logger.error(
                "Failed to save L3 prompt %s_%s: %s", cell_id, query_type, e
            )
            if "prompts" not in cell:
                cell["prompts"] = {}
            cell["prompts"].setdefault(query_type, None)

    logger.info("Batch L3 prompt generation complete.")

    # -----------------------------------------------------------------------
    # Post-generation validation pass: check ALL prompts (including any that
    # were already on disk before this run) against Parallel size limits.
    # -----------------------------------------------------------------------
    _validate_and_compress_existing_prompts(all_items, llm)


# ---------------------------------------------------------------------------
# Main postprocessing per venue
# ---------------------------------------------------------------------------

def _load_venue_inputs(venue: dict) -> dict | None:
    """
    Load all disk inputs for one venue without calling the LLM.

    Checks for 2A_structure.json and jurisdiction_card.json.
    Loads venue_card.json from disk if it already exists (idempotency).

    Returns a dict with keys:
        venue, venue_key, raw_2a, jurisdiction_card,
        venue_card (VenueCard | None), card_path, cells_path
    or None if required input files are missing or unreadable.
    """
    venue_key = venue["venue_key"]
    name_ru = venue["name_ru"]
    d = get_country_level2_dir(name_ru, venue_key)

    path_2a = d / "2A_structure.json"
    if not path_2a.exists():
        logger.warning(
            "Skipping postprocessing for %s: 2A_structure.json not found at %s",
            venue_key,
            path_2a,
        )
        return None

    card_path = d / "venue_card.json"
    cells_path = d / "cells_list.json"

    raw_2a = load_json(path_2a)
    if raw_2a is None:
        logger.error("Failed to load 2A_structure.json for %s", venue_key)
        return None

    card_l1_path = get_country_level1_dir(name_ru) / "jurisdiction_card.json"
    jurisdiction_card = load_json(card_l1_path)
    if jurisdiction_card is None:
        logger.error("jurisdiction_card.json not found for %s", name_ru)
        return None

    # Load cached VenueCard if present (no LLM call here)
    venue_card: VenueCard | None = None
    if card_path.exists():
        logger.info("VenueCard for %s already exists, loading from disk.", venue_key)
        raw_card = load_json(card_path)
        venue_card = VenueCard.model_validate(raw_card)

    return {
        "venue": venue,
        "venue_key": venue_key,
        "raw_2a": raw_2a,
        "jurisdiction_card": jurisdiction_card,
        "venue_card": venue_card,
        "card_path": card_path,
        "cells_path": cells_path,
    }


def _build_cells(inp: dict) -> list[dict]:
    """
    Build the cells skeleton for a venue whose VenueCard has already been resolved.
    Cells are derived from VenueCard.instrument_coverage (Question B result).
    Preserves existing prompt paths from cells_list.json if present.

    Cell schema:
        cell_id, venue_key, tier, instrument_class,
        secondary_admission_applicable, distinct_regime, legacy, modifiers, prompts
    """
    venue = inp["venue"]
    venue_key = inp["venue_key"]
    venue_card: VenueCard = inp["venue_card"]
    cells_path: Path = inp["cells_path"]

    iso = _iso_country_code(venue["name_en"])
    cells: list[dict] = []

    existing_cells_data = load_json(cells_path) if cells_path.exists() else None
    existing_cells_by_id: dict[str, dict] = {}
    if existing_cells_data:
        for c in existing_cells_data.get("cells", []):
            existing_cells_by_id[c["cell_id"]] = c

    # Soft validation: warn if segment has generates_cell=True but no rulebook_chapters.
    # Does NOT override — flags for human review (at scale, aggregate into audit report).
    for seg in venue_card.segments:
        if seg.generates_cell and not seg.rulebook_chapters:
            logger.warning(
                "Venue %s: segment '%s' has generates_cell=true but no rulebook_chapters "
                "specified. Verify that this segment has distinct admission criteria.",
                venue_key,
                seg.segment_name,
            )

    for coverage in venue_card.instrument_coverage:
        # Determine cell_id
        if coverage.segment:
            slug = _tier_slug(coverage.segment)
            cell_id = f"{iso}_{venue_key}_{coverage.instrument_class}_{slug}"
        elif coverage.regime_name:
            slug = _tier_slug(coverage.regime_name)
            cell_id = f"{iso}_{venue_key}_{slug}_{coverage.instrument_class}"
        else:
            cell_id = f"{iso}_{venue_key}_{coverage.instrument_class}"

        # Determine display label (used in prompts as "tier")
        if coverage.segment:
            tier_label = coverage.segment
        elif coverage.distinct_regime and coverage.regime_name:
            tier_label = coverage.regime_name
        elif coverage.legacy and coverage.regime_name:
            tier_label = coverage.regime_name
        elif coverage.regime_name:
            tier_label = coverage.regime_name
        else:
            tier_label = "(no listing tiers — flat structure)"

        if cell_id in existing_cells_by_id:
            cells.append(existing_cells_by_id[cell_id])
        else:
            cells.append({
                "cell_id": cell_id,
                "venue_key": venue_key,
                "tier": tier_label,
                "instrument_class": coverage.instrument_class,
                "secondary_admission_applicable": coverage.secondary_admission_applicable or coverage.distinct_regime,
                "distinct_regime": coverage.distinct_regime,
                "legacy": coverage.legacy,
                "admission_path": coverage.admission_path,
                "segment": coverage.segment,
                "modifiers": coverage.modifiers,
                "prompts": {"3A": None, "3B": None, "3C": None},
            })

    return cells


def _prepare_venue(venue: dict) -> dict | None:
    """
    Load inputs and extract VenueCard for one venue via LLM (single-venue path).
    Builds the skeleton cells list (without prompt paths yet).

    Returns a dict with keys:
        venue, venue_card, raw_2a, cells, jurisdiction_card,
        cells_path, venue_key
    or None if inputs are missing or extraction fails.
    """
    inp = _load_venue_inputs(venue)
    if inp is None:
        return None

    # If VenueCard was not cached, call LLM now (single-venue flow)
    if inp["venue_card"] is None:
        try:
            card = _build_venue_card(inp["venue"], inp["raw_2a"], inp["jurisdiction_card"])
        except Exception as e:
            logger.error("LLM VenueCard extraction failed for %s: %s", inp["venue_key"], e)
            return None
        save_json(inp["card_path"], card.model_dump())
        logger.info("Saved venue_card.json for %s", inp["venue_key"])
        inp["venue_card"] = card

    cells = _build_cells(inp)

    return {
        "venue": inp["venue"],
        "venue_key": inp["venue_key"],
        "venue_card": inp["venue_card"],
        "raw_2a": inp["raw_2a"],
        "cells": cells,
        "jurisdiction_card": inp["jurisdiction_card"],
        "cells_path": inp["cells_path"],
    }


def process_venue(venue: dict, cells_only: bool = False) -> bool:
    """
    Run LLM postprocessing for one venue (single-venue entry point).
    Uses batch L3 prompt generation internally unless cells_only=True.

    cells_only=True: only extract VenueCard and build cells_list.json,
    skip L3 prompt generation. Use during L2 structure validation.

    Returns True on success, False if inputs are missing or error.
    """
    vd = _prepare_venue(venue)
    if vd is None:
        return False

    if not cells_only:
        generate_all_level3_prompts([vd])

    # Save cells_list.json
    cells_data = {
        "venue_key": vd["venue_key"],
        "jurisdiction_ru": venue["name_ru"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cells": vd["cells"],
    }
    save_json(vd["cells_path"], cells_data)
    logger.info(
        "Saved cells_list.json for %s (%d cells)",
        vd["venue_key"],
        len(vd["cells"]),
    )
    return True


def process_all(cells_only: bool = False, venues: list = None) -> dict:
    """
    Run postprocessing for all PILOT_VENUES (or a provided venues list).

    Phase 1a: Load disk inputs for all venues (no LLM).
    Phase 1b: Batch VenueCard extraction for venues without a cached card.
    Phase 2:  Batch-generate all Level 3 prompts (skipped if cells_only=True).
    Phase 3:  Save cells_list.json for each venue.

    cells_only=True: skip L3 generation, use for L2 structure validation.
    venues: optional list of venue config dicts; defaults to PILOT_VENUES.
    """
    venues_data: list[dict] = []
    failed: list[str] = []

    _venues = venues if venues is not None else PILOT_VENUES

    # --- Phase 1a: load inputs for all venues ---
    loaded: list[dict] = []
    for venue in _venues:
        inp = _load_venue_inputs(venue)
        if inp is None:
            failed.append(venue["venue_key"])
            continue
        loaded.append(inp)

    # --- Phase 1b: batch VenueCard extraction for venues without cached card ---
    to_extract = [inp for inp in loaded if inp["venue_card"] is None]
    if to_extract:
        prompts = [
            _build_venue_prompt(inp["venue"], inp["raw_2a"], inp["jurisdiction_card"])
            for inp in to_extract
        ]
        llm = _get_llm()
        chain = llm.with_structured_output(VenueCard, method="function_calling")
        logger.info(
            "Batching VenueCard extraction for %d venues (max_concurrency=50)...",
            len(to_extract),
        )
        remaining_prompts = list(enumerate(prompts))  # [(original_idx, prompt), ...]
        cards_map: dict[int, Any] = {}
        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            if not remaining_prompts:
                break
            inputs = [[HumanMessage(content=p)] for _, p in remaining_prompts]
            raw = chain.batch(inputs, config={"max_concurrency": 50}, return_exceptions=True)
            still_failing = []
            for (orig_idx, p), result in zip(remaining_prompts, raw):
                if isinstance(result, Exception):
                    logger.warning(
                        "VenueCard extraction: request %d failed on attempt %d: %s",
                        orig_idx, attempt, result,
                    )
                    still_failing.append((orig_idx, p))
                else:
                    cards_map[orig_idx] = result
            remaining_prompts = still_failing
            if still_failing and attempt < max_attempts:
                logger.info("Retrying %d failed VenueCard extractions (attempt %d/%d)...", len(still_failing), attempt + 1, max_attempts)

        if remaining_prompts:
            failed_indices = [i for i, _ in remaining_prompts]
            logger.error("VenueCard extraction: %d requests failed after %d attempts: indices %s", len(remaining_prompts), max_attempts, failed_indices)

        cards = [cards_map.get(i) for i in range(len(prompts))]
        for inp, card in zip(to_extract, cards):
            if card is None:
                logger.error("VenueCard for %s: extraction failed, skipping.", inp["venue"].get("venue_key", "?"))
                continue
            inp["venue_card"] = card
            save_json(inp["card_path"], card.model_dump())
            logger.info("Saved venue_card.json for %s", inp["venue_key"])

    # Build cells skeletons and assemble venues_data
    for inp in loaded:
        cells = _build_cells(inp)
        venues_data.append({
            "venue": inp["venue"],
            "venue_key": inp["venue_key"],
            "venue_card": inp["venue_card"],
            "raw_2a": inp["raw_2a"],
            "cells": cells,
            "jurisdiction_card": inp["jurisdiction_card"],
            "cells_path": inp["cells_path"],
        })

    # --- Phase 2: batch generate all L3 prompts ---
    if venues_data and not cells_only:
        generate_all_level3_prompts(venues_data)
    elif cells_only:
        logger.info("cells_only mode — skipping L3 prompt generation.")

    # --- Phase 3: save cells_list.json for each venue ---
    results = {}
    for vd in venues_data:
        venue_key = vd["venue_key"]
        venue = vd["venue"]
        cells_data = {
            "venue_key": venue_key,
            "jurisdiction_ru": venue["name_ru"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cells": vd["cells"],
        }
        save_json(vd["cells_path"], cells_data)
        logger.info(
            "Saved cells_list.json for %s (%d cells)", venue_key, len(vd["cells"])
        )
        results[venue_key] = "done"

    for venue_key in failed:
        results[venue_key] = "skipped/failed"

    logger.info("=== Level 2 postprocessing summary ===")
    for key, status in results.items():
        logger.info("  %s: %s", key, status)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Level 2 LLM postprocessor")
    parser.add_argument(
        "--venue",
        type=str,
        default=None,
        help="venue_key to process (e.g. LSE_Main_Market). If omitted, process all pilot venues.",
    )
    parser.add_argument(
        "--cells-only",
        action="store_true",
        default=False,
        help="Only extract VenueCard and build cells_list.json; skip L3 prompt generation. "
             "Use during L2 structure validation.",
    )
    args = parser.parse_args()

    if args.venue:
        from pipeline.config import VENUE_BY_KEY
        venue = VENUE_BY_KEY.get(args.venue)
        if not venue:
            logger.error("Unknown venue key: %s", args.venue)
            sys.exit(1)
        process_venue(venue, cells_only=args.cells_only)
    else:
        process_all(cells_only=args.cells_only)
