"""
Level 3 v2: Launch and poll Parallel Deep Research tasks per venue × instrument_class.

New architecture (pipeline_patch_variant_b):
- Unit: venue × instrument_class (all tiers in one request)
- Prompts: algorithmic (no LLM), 9-block template
- Schema: array-based tiers[]
- Processor: pro for all task types
"""
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.config import (
    LEVEL3_V2_STATE_FILE,
    LEVEL3_V2_LOG_FILE,
    PROMPTS_LEVEL3_V2_DIR,
    PILOT_VENUES,
    LOGS_DIR,
    get_country_level1_dir,
    get_country_level2_dir,
    get_country_level3_dir,
)
from pipeline.storage import load_json, save_json, save_prompt, now_iso
from pipeline.parallel_runner import launch_task, poll_all, save_state as _runner_save_state
from pipeline.logging_setup import get_logger

logger = get_logger("venue_runner_v2", LEVEL3_V2_LOG_FILE)


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

def _desc_source_obj(description_hint: str) -> dict:
    """Return a schema object with description and source fields."""
    return {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": description_hint,
            },
            "source": {"type": "string"},
        },
    }


# ---------------------------------------------------------------------------
# SCHEMA_3A_V2 — primary admission requirements (array-based)
# ---------------------------------------------------------------------------

SCHEMA_3A_V2 = {
    "type": "object",
    "properties": {
        "tiers": {
            "type": "array",
            "description": (
                "One element per listing tier or category found for this instrument class "
                "on this venue. If venue has no tiered structure — single element with "
                "tier_name 'flat'."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "tier_name": {
                        "type": "string",
                        "description": (
                            "Official name of the listing tier or category. "
                            "Use 'flat' if no tiered structure exists."
                        ),
                    },
                    "admission_overview": _desc_source_obj(
                        "Overall admission regime: main paths/tests for eligibility, structure "
                        "of the process, key decision points, alternative routes. Be specific "
                        "— list each test/path with conditions."
                    ),
                    "eligibility_requirements": _desc_source_obj(
                        "Requirements to the ISSUER: financial history (years, audited accounts), "
                        "profitability tests (thresholds, calculation, alternatives), assets/equity "
                        "minimums, revenue requirements, working capital, corporate governance "
                        "standards, board composition, auditor requirements, accounting standards. "
                        "For each requirement: state the exact value/threshold, how it is "
                        "calculated, what is included/excluded, whether alternatives exist, "
                        "whether it varies by issuer type/size."
                    ),
                    "instrument_requirements": _desc_source_obj(
                        "Requirements to the INSTRUMENT: free float (percentage, calculation "
                        "methodology, what is excluded from float, verification), minimum market "
                        "capitalisation (value, currency, which test), minimum number of "
                        "shareholders (threshold, definition of qualifying holder), minimum share "
                        "price, minimum issue size/volume. For each: exact value, calculation, "
                        "exclusions, alternatives, links to other requirements."
                    ),
                    "sponsor_and_infrastructure": _desc_source_obj(
                        "Sponsor/nominated adviser: mandatory or optional, role, responsibilities, "
                        "liability. Market maker/liquidity provider: required or not, conditions. "
                        "Prospectus/information document: required, who approves, which regulation "
                        "governs content."
                    ),
                    "restrictions_and_lock_ups": _desc_source_obj(
                        "Lock-up periods: duration, who is subject (controlling shareholders, "
                        "management, cornerstone investors), conditions for release. Escrow "
                        "arrangements. Any other post-admission restrictions on share sales."
                    ),
                    "procedure_and_timeline": _desc_source_obj(
                        "Application procedure: documents required, submission process, review "
                        "stages, decision timeline, approval/rejection, appeal mechanism. Typical "
                        "end-to-end timeline from application to first trading day."
                    ),
                    "disclosure_at_admission": _desc_source_obj(
                        "Prospectus or admission document requirements: content requirements, "
                        "approval authority, language, format. Pre-admission announcements."
                    ),
                    "special_regimes": _desc_source_obj(
                        "Modifications to standard requirements for specific issuer types: SPAC, "
                        "dual-class/WVR shares, biotech/pre-revenue companies, mineral companies, "
                        "foreign issuers, shell companies. For each: which standard requirements "
                        "are modified and how."
                    ),
                    "secondary_admission": _desc_source_obj(
                        "If a secondary listing / cross-listing regime exists on this tier: "
                        "eligibility (qualifying exchanges, market cap), which standard requirements "
                        "are waived or modified, additional requirements, continuing obligations "
                        "differences. State 'not applicable' if no secondary regime."
                    ),
                    "additional_findings": _desc_source_obj(
                        "Any significant requirements, conditions, or procedures not covered by "
                        "the fields above."
                    ),
                },
            },
        },
        "common_requirements": _desc_source_obj(
            "Requirements that apply equally to ALL tiers/categories of this instrument class "
            "on this venue, if any. Avoids duplication across tier elements."
        ),
    },
}


# ---------------------------------------------------------------------------
# SCHEMA_3B_V2 — continuing obligations, suspension, delisting (array-based)
# ---------------------------------------------------------------------------

SCHEMA_3B_V2 = {
    "type": "object",
    "properties": {
        "tiers": {
            "type": "array",
            "description": (
                "One element per listing tier or category found for this instrument class "
                "on this venue. If venue has no tiered structure — single element with "
                "tier_name 'flat'."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "tier_name": {"type": "string"},
                    "continuing_obligations": {
                        "type": "object",
                        "properties": {
                            "quantitative_thresholds": _desc_source_obj(
                                "Financial and operational thresholds that must be maintained "
                                "post-admission: minimum market cap, minimum float, minimum "
                                "shareholders, financial ratios. Exact values, calculation "
                                "method, monitoring frequency."
                            ),
                            "qualitative_obligations": _desc_source_obj(
                                "Board composition, corporate governance, related-party "
                                "transaction rules, insider dealing policies, whistleblowing, "
                                "ESG disclosure. For each: exact rule and what is required."
                            ),
                            "periodic_reporting": _desc_source_obj(
                                "Reporting schedule: annual reports (deadline after year-end), "
                                "interim/half-year reports (deadline), quarterly reports (if "
                                "required), ad-hoc disclosure triggers. Accounting standards "
                                "required post-admission."
                            ),
                            "compliance_confirmation": _desc_source_obj(
                                "Annual compliance confirmation requirements: form, addressee, "
                                "deadline, content (self-assessment vs. external audit). "
                                "Corporate governance statement obligations."
                            ),
                        },
                    },
                    "suspension": {
                        "type": "object",
                        "properties": {
                            "grounds": _desc_source_obj(
                                "Grounds for suspension: regulatory grounds (pending announcement, "
                                "disclosure failure), exchange discretion grounds, issuer-requested "
                                "suspension. List each ground explicitly."
                            ),
                            "procedure": _desc_source_obj(
                                "Who initiates suspension (exchange vs. regulator), notification "
                                "requirements, issuer rights during suspension, appeal mechanism."
                            ),
                            "duration_limits": _desc_source_obj(
                                "Maximum permitted suspension period before mandatory action "
                                "(delisting or reinstatement). Any time-based review milestones."
                            ),
                            "disclosure": _desc_source_obj(
                                "Disclosure requirements when suspension is imposed: announcement "
                                "content, timing, channels. Ongoing disclosure obligations during "
                                "suspension period."
                            ),
                        },
                    },
                    "delisting_compulsory": {
                        "type": "object",
                        "properties": {
                            "grounds": _desc_source_obj(
                                "Grounds for compulsory delisting: failure to maintain listing "
                                "criteria, prolonged suspension, insolvency, regulatory action. "
                                "List each ground with specific trigger conditions."
                            ),
                            "procedure": _desc_source_obj(
                                "Decision-making process: who decides, notice period to issuer, "
                                "right to make representations, final decision authority."
                            ),
                            "grace_period": _desc_source_obj(
                                "Any period allowed to remedy the deficiency before delisting "
                                "is effected. Duration, conditions, extension possibilities."
                            ),
                            "shareholder_protection": _desc_source_obj(
                                "Measures to protect shareholders in compulsory delisting: "
                                "shareholder vote requirement (if any), mandatory offer "
                                "obligations, exit opportunities, compensation mechanisms."
                            ),
                            "disclosure": _desc_source_obj(
                                "Announcement obligations: when the issuer must announce, "
                                "what must be disclosed, effective date announcement."
                            ),
                        },
                    },
                    "delisting_voluntary": {
                        "type": "object",
                        "properties": {
                            "conditions": _desc_source_obj(
                                "Conditions precedent for voluntary delisting: minimum listing "
                                "period, shareholder approval threshold, regulatory consent. "
                                "Exact requirements."
                            ),
                            "procedure": _desc_source_obj(
                                "Application process, notice periods, exchange approval, "
                                "timeline from application to effective delisting date."
                            ),
                            "shareholder_approval": _desc_source_obj(
                                "Shareholder vote: threshold required (majority, supermajority, "
                                "special resolution), who can vote, any mandatory offer "
                                "requirement triggered by voluntary delisting."
                            ),
                        },
                    },
                    "terminology": {
                        "type": "object",
                        "properties": {
                            "delisting_local_term": {"type": "string"},
                            "suspension_local_term": {"type": "string"},
                            "source": {"type": "string"},
                        },
                    },
                    "additional_findings": _desc_source_obj(
                        "Significant obligations, procedures, or provisions not covered above."
                    ),
                },
            },
        },
        "common_obligations": _desc_source_obj(
            "Obligations that apply equally to ALL tiers of this instrument class on this venue."
        ),
    },
}


# ---------------------------------------------------------------------------
# SCHEMA_3C_V2 — monitoring and enforcement (array-based)
# ---------------------------------------------------------------------------

SCHEMA_3C_V2 = {
    "type": "object",
    "properties": {
        "tiers": {
            "type": "array",
            "description": (
                "One element per listing tier or category found for this instrument class "
                "on this venue. If venue has no tiered structure — single element with "
                "tier_name 'flat'."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "tier_name": {"type": "string"},
                    "monitoring_regime": {
                        "type": "object",
                        "properties": {
                            "responsible_body": _desc_source_obj(
                                "Who is responsible for ongoing monitoring: exchange surveillance "
                                "team, listing compliance team, external regulator. Division of "
                                "responsibilities between exchange and regulator."
                            ),
                            "mechanisms": _desc_source_obj(
                                "Monitoring tools and mechanisms: trading surveillance systems, "
                                "periodic filing reviews, ad-hoc disclosure reviews, on-site "
                                "inspections, third-party audits. How each mechanism operates."
                            ),
                            "sponsor_role": _desc_source_obj(
                                "Role of sponsor/nominated adviser in ongoing monitoring: "
                                "obligations to exchange, reporting duties, liability for issuer "
                                "compliance failures. If no sponsor required — state 'not applicable'."
                            ),
                            "issuer_reporting_to_exchange": _desc_source_obj(
                                "Issuer's direct reporting obligations to the exchange (beyond "
                                "public disclosure): compliance certificates, annual confirmations, "
                                "pre-clearance requirements, notification of corporate actions."
                            ),
                        },
                    },
                    "sanctions": {
                        "type": "object",
                        "properties": {
                            "exchange_sanctions": _desc_source_obj(
                                "Sanctions available to the exchange: public censure, private "
                                "warning, financial fine (amount range), trading suspension, "
                                "cancellation of listing. Triggering conditions for each."
                            ),
                            "regulator_sanctions": _desc_source_obj(
                                "Sanctions available to the regulator (if different from exchange): "
                                "fines, licence revocation, criminal referral, civil proceedings. "
                                "Jurisdiction between exchange and regulator."
                            ),
                            "disciplinary_procedure": _desc_source_obj(
                                "Disciplinary process: initiation, investigation, notice to issuer, "
                                "right of response, hearing, decision, appeal. Timeline for each stage."
                            ),
                            "publication_of_actions": _desc_source_obj(
                                "Publication policy: which sanctions are made public, format of "
                                "publication, naming of issuers, historical database access."
                            ),
                        },
                    },
                    "enforcement_practice": {
                        "type": "object",
                        "properties": {
                            "recent_examples": _desc_source_obj(
                                "Recent enforcement actions (last 3–5 years): issuer name (if "
                                "public), sanction imposed, nature of breach, outcome. Cite "
                                "specific cases where available."
                            ),
                            "general_approach": _desc_source_obj(
                                "General enforcement philosophy: reactive vs. proactive, "
                                "frequency of actions, areas of focus, published enforcement "
                                "priorities."
                            ),
                        },
                    },
                    "additional_findings": _desc_source_obj(
                        "Significant monitoring provisions, sanctions, or enforcement practices "
                        "not covered above."
                    ),
                },
            },
        },
        "common_monitoring": _desc_source_obj(
            "Monitoring provisions applying to ALL tiers of this instrument class on this venue."
        ),
    },
}


# Unified schema lookup
SCHEMAS_V2 = {"3A": SCHEMA_3A_V2, "3B": SCHEMA_3B_V2, "3C": SCHEMA_3C_V2}


# ---------------------------------------------------------------------------
# Size check helper
# ---------------------------------------------------------------------------

PARALLEL_MAX_CHARS = 15000  # prompt + schema combined limit


def _combined_size(prompt_text: str, schema: dict) -> int:
    schema_str = json.dumps({"type": "json", "json_schema": schema})
    return len(prompt_text) + len(schema_str)


# ---------------------------------------------------------------------------
# Prompt builder (9-block template)
# ---------------------------------------------------------------------------

_QUERY_TOPIC = {
    "3A": (
        "primary admission requirements (eligibility criteria, admission procedures, "
        "disclosure obligations, and special regimes)"
    ),
    "3B": (
        "continuing obligations, suspension grounds and procedure, and delisting rules "
        "(both compulsory and voluntary)"
    ),
    "3C": (
        "monitoring and enforcement regime (post-admission monitoring, sanctions, "
        "enforcement practice)"
    ),
}

_DEFINITIONS_BLOCK = """DEFINITIONS (use consistently throughout your research):
- Venue: a specific trading platform or stock exchange where securities are listed and/or traded.
- Listing tier: a distinct admission category within a venue that has its own specific admission criteria (e.g., Main Board, GEM, Premium, Standard).
- Thematic segment: an organisational or marketing grouping within a venue that does NOT impose its own separate admission criteria.
- Modifier: a special regime applied on top of standard tier requirements (e.g., SPAC track, dual-class/WVR shares, shell company fast-track).
- IMPORTANT: Instrument-class chapters in a rulebook are NOT tiers. Rulebook chapter organisation does not define venue structure."""

_DEPTH_BLOCK = """DEPTH REQUIREMENT:
For each requirement, threshold, or condition found:
- State the exact value, unit, or formula
- Explain how it is calculated (inclusions, exclusions, verification mechanism)
- State whether alternatives exist (either/or paths, equivalents)
- State whether it varies by company size, type, or other factors
- State whether it is linked to other requirements (combined thresholds, dependencies)
Do NOT summarise — provide full detail for every requirement found. These details will be used for systematic cross-jurisdiction comparison."""

_CLOSING_BLOCK = """Include any relevant provisions from chapters or regulations beyond those mentioned above.
Cite specific rule/section numbers for each finding."""


def build_prompt(
    venue_card: dict,
    jurisdiction_card: dict,
    instrument_class: str,
    query_type: str,
) -> str:
    """
    Build an algorithmic 9-block prompt for venue × instrument_class × query_type.
    Returns prompt string.
    """
    venue_name = venue_card.get("venue_name_english") or venue_card.get("venue_name_ru", "")
    operator = venue_card.get("operator", "")
    jurisdiction_en = jurisdiction_card.get("jurisdiction", "")
    venue_type = venue_card.get("venue_type", "regulated market").replace("_", " ")

    # Tiers relevant to this instrument_class
    all_tiers = venue_card.get("tiers", [])
    relevant_tiers = [
        t for t in all_tiers
        if instrument_class in t.get("instrument_classes", [])
    ]
    tier_names = [t.get("tier_name_ru") or t.get("tier_name", "") for t in relevant_tiers]

    # Fallback: derive from instrument_coverage if tiers is empty for this class
    if not tier_names:
        ic_list_all = venue_card.get("instrument_coverage", [])
        tier_names = [
            ic.get("regime_name") or ic.get("regime_name_ru") or ic.get("instrument_class", "")
            for ic in ic_list_all
            if ic.get("instrument_class") == instrument_class and not ic.get("legacy")
        ]

    tiers_str = ", ".join(tier_names) if tier_names else "flat (no tiered structure)"

    # Legacy instrument_coverage entries for this class
    ic_list = venue_card.get("instrument_coverage", [])
    legacy_names = [
        ic.get("regime_name_ru") or ic.get("regime_name") or ic.get("instrument_class", "")
        for ic in ic_list
        if ic.get("instrument_class") == instrument_class and ic.get("legacy")
    ]

    # Split architecture check
    arch = (jurisdiction_card.get("admission_architecture") or "").lower()
    is_split = any(keyword in arch for keyword in ("split", "separate", "two-gate", "dual", "distinct"))
    listing_authority = jurisdiction_card.get("listing_authority") or "listing authority"

    # Supranational check
    is_supranational = jurisdiction_card.get("supranational_flag", False)
    supranational_framework = jurisdiction_card.get("supranational_framework", "")

    topic = _QUERY_TOPIC.get(query_type, "admission requirements")

    # --- Build blocks ---
    blocks = []

    # BLOCK 1: Venue context
    blocks.append(
        f"VENUE CONTEXT:\n"
        f"Venue: {venue_name}\n"
        f"Operator: {operator}\n"
        f"Jurisdiction: {jurisdiction_en}\n"
        f"Market type: {venue_type}\n"
        f"Listing tiers/categories for {instrument_class}: {tiers_str}"
    )

    # BLOCK 2: Definitions
    blocks.append(_DEFINITIONS_BLOCK)

    # BLOCK 3: Research task
    blocks.append(
        f"RESEARCH TASK:\n"
        f"Research {topic} for {instrument_class} on {venue_name} in {jurisdiction_en}.\n"
        f"Cover ALL listing tiers and categories of {instrument_class} on this venue.\n"
        f"Known tiers/categories: {tiers_str}"
    )

    # BLOCK 4: Split architecture (conditional)
    if is_split:
        exchange_name = venue_name
        blocks.append(
            f"SPLIT ARCHITECTURE NOTE:\n"
            f"This jurisdiction separates official listing from admission to trading.\n"
            f"Cover requirements from BOTH the listing authority ({listing_authority}) "
            f"AND the exchange ({exchange_name}).\n"
            f"Also cover the admission-to-trading-only path if it exists on this venue."
        )

    # BLOCK 5: Supranational framework (conditional)
    if is_supranational and supranational_framework:
        blocks.append(
            f"SUPRANATIONAL FRAMEWORK NOTE:\n"
            f"This jurisdiction is subject to {supranational_framework}.\n"
            f"Indicate which requirements are set at supranational level "
            f"and which at national/venue level."
        )

    # BLOCK 6: Depth instruction
    blocks.append(_DEPTH_BLOCK)

    # BLOCK 7: Structure by tiers
    blocks.append(
        f"RESPONSE STRUCTURE:\n"
        f"Structure your response by listing tier/category.\n"
        f"Known tiers for {instrument_class} on {venue_name}: {tiers_str}\n"
        f"If you find additional tiers/categories not listed above — include them.\n"
        f"If the venue has no tiered structure — use a single entry with tier_name 'flat'."
    )

    # BLOCK 8: Legacy categories (conditional)
    if legacy_names:
        legacy_list = ", ".join(legacy_names)
        blocks.append(
            f"LEGACY/TRANSITION CATEGORIES:\n"
            f"The following categories are closed to new admissions (grandfathering/transition): "
            f"{legacy_list}.\n"
            f"Do NOT research primary admission requirements for these categories."
        )

    # BLOCK 9: Closing instruction
    blocks.append(_CLOSING_BLOCK)

    return "\n\n---\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Task list builder
# ---------------------------------------------------------------------------

def _get_instrument_classes_for_venue(venue_card: dict) -> list[str]:
    """Extract unique instrument classes from venue_card.instrument_coverage."""
    seen = []
    for ic in venue_card.get("instrument_coverage", []):
        cls = ic.get("instrument_class")
        if cls and cls not in seen:
            seen.append(cls)
    return seen


def _build_task_list(venues: list = None) -> list[dict]:
    """
    Build flat list of task descriptors: venue × instrument_class × query_type.
    Each entry: {task_key, venue_key, name_ru, instrument_class, query_type,
                 venue_card, jurisdiction_card}
    """
    tasks = []
    for venue in (venues or PILOT_VENUES):
        venue_key = venue["venue_key"]
        name_ru = venue["name_ru"]

        venue_card_path = get_country_level2_dir(name_ru, venue_key) / "venue_card.json"
        venue_card = load_json(venue_card_path)
        if not venue_card:
            logger.error("venue_card.json not found for %s — skipping", venue_key)
            continue

        jcard_path = get_country_level1_dir(name_ru) / "jurisdiction_card.json"
        jurisdiction_card = load_json(jcard_path)
        if not jurisdiction_card:
            logger.error("jurisdiction_card.json not found for %s — skipping", name_ru)
            continue

        instrument_classes = _get_instrument_classes_for_venue(venue_card)
        if not instrument_classes:
            logger.warning("No instrument classes found for venue %s — skipping", venue_key)
            continue

        for instrument_class in instrument_classes:
            for query_type in ("3A", "3B", "3C"):
                task_key = f"{venue_key}_{instrument_class}_{query_type}"
                tasks.append({
                    "task_key": task_key,
                    "venue_key": venue_key,
                    "name_ru": name_ru,
                    "instrument_class": instrument_class,
                    "query_type": query_type,
                    "venue_card": venue_card,
                    "jurisdiction_card": jurisdiction_card,
                })

    return tasks


# ---------------------------------------------------------------------------
# Save raw result helper
# ---------------------------------------------------------------------------

def _make_raw_save_fn(venue_key: str, name_ru: str, instrument_class: str, query_type: str):
    """Return save function that writes raw Parallel result to _parallel_raw/ subfolder."""
    raw_dir = get_country_level3_dir(name_ru, venue_key) / "_parallel_raw"

    def save_fn(content) -> Path:
        raw_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{venue_key}_{instrument_class}_{query_type}_raw.json"
        path = raw_dir / filename
        data = {
            "venue_key": venue_key,
            "instrument_class": instrument_class,
            "query_type": query_type,
            "retrieved_at": now_iso(),
            "parallel_output": content,  # full parallel_output (basis, content, type, ...)
            "content": content.get("content", {}) if isinstance(content, dict) else content,  # inner research data
        }
        save_json(path, data)
        logger.info(
            "Saved %s (parallel_output: %s, content keys: %s)",
            filename,
            "yes" if isinstance(content, dict) and "basis" in content else "no",
            list(content.get("content", {}).keys())[:3] if isinstance(content, dict) and isinstance(content.get("content"), dict) else "N/A",
        )
        return path

    return save_fn


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    data = load_json(LEVEL3_V2_STATE_FILE)
    return data if data is not None else {"tasks": {}}


def save_state(state: dict) -> None:
    _runner_save_state(state, LEVEL3_V2_STATE_FILE)


# ---------------------------------------------------------------------------
# Build and save prompts
# ---------------------------------------------------------------------------

def build_and_save_all_prompts(state: dict, venues: list = None) -> None:
    """Build prompts algorithmically and save to PROMPTS_LEVEL3_V2_DIR. Store paths in state."""
    task_list = _build_task_list(venues)
    logger.info("Building prompts for %d tasks", len(task_list))
    PROMPTS_LEVEL3_V2_DIR.mkdir(parents=True, exist_ok=True)

    for item in task_list:
        task_key = item["task_key"]
        prompt_text = build_prompt(
            venue_card=item["venue_card"],
            jurisdiction_card=item["jurisdiction_card"],
            instrument_class=item["instrument_class"],
            query_type=item["query_type"],
        )
        schema = SCHEMAS_V2[item["query_type"]]
        combined = _combined_size(prompt_text, schema)

        if combined > PARALLEL_MAX_CHARS:
            logger.warning(
                "Prompt for %s exceeds %d chars (%d) — consider splitting by instrument class",
                task_key, PARALLEL_MAX_CHARS, combined
            )

        prompt_filename = f"{item['venue_key']}_{item['instrument_class']}_{item['query_type']}"
        save_prompt(PROMPTS_LEVEL3_V2_DIR, prompt_filename, prompt_text)
        prompt_path = PROMPTS_LEVEL3_V2_DIR / f"{prompt_filename}.txt"

        # Store prompt path in state for reference
        if task_key not in state.get("prompts", {}):
            state.setdefault("prompts", {})[task_key] = str(prompt_path)

        logger.info("Prompt saved: %s (%d chars combined)", prompt_filename, combined)

    save_state(state)
    logger.info("All prompts built and saved.")


# ---------------------------------------------------------------------------
# Launch and poll
# ---------------------------------------------------------------------------

def launch_all_venues(state: dict, venues: list = None) -> None:
    """Launch Parallel L3 tasks for all venue × instrument_class combinations."""
    task_list = _build_task_list(venues)
    logger.info(
        "Launching %d Parallel tasks (venue × instrument_class × query_type)", len(task_list)
    )

    for item in task_list:
        task_key = item["task_key"]
        prompt_filename = f"{item['venue_key']}_{item['instrument_class']}_{item['query_type']}"
        prompt_path = PROMPTS_LEVEL3_V2_DIR / f"{prompt_filename}.txt"

        if not prompt_path.exists():
            logger.error(
                "Prompt file not found for %s: %s — skipping", task_key, prompt_path
            )
            continue

        with open(prompt_path, encoding="utf-8") as f:
            prompt_text = f.read()

        launch_task(
            task_key=task_key,
            prompt=prompt_text,
            output_schema=SCHEMAS_V2[item["query_type"]],
            processor="pro",
            state=state,
            state_file=LEVEL3_V2_STATE_FILE,
        )

    save_state(state)
    logger.info("All venue-level L3 tasks launched.")


def poll_all_venues(state: dict, venues: list = None) -> dict:
    """Poll all venue-level L3 tasks until complete."""
    task_list = _build_task_list(venues)
    tasks_to_poll = []

    for item in task_list:
        task_key = item["task_key"]
        if task_key not in state["tasks"]:
            logger.warning("Task %s not in state — was it launched?", task_key)
            continue
        save_fn = _make_raw_save_fn(
            venue_key=item["venue_key"],
            name_ru=item["name_ru"],
            instrument_class=item["instrument_class"],
            query_type=item["query_type"],
        )
        tasks_to_poll.append((task_key, save_fn))

    return poll_all(tasks_to_poll, state, state_file=LEVEL3_V2_STATE_FILE)
