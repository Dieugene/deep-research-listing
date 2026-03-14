"""
Level 2: Generate 2A Deep Research prompts for each venue using LLM (gpt-5).

The LLM generates a custom English-language prompt that uses exact local
terminology from the jurisdiction_card produced at Level 1.

Usage:
    python -m level_2.prompt_generator   # generate for all PILOT_VENUES
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from langchain_openai import ChatOpenAI

from pipeline.config import (
    LLM_FAST_MODEL,
    PILOT_VENUES,
    PROMPTS_LEVEL2_DIR,
    get_country_level1_dir,
)
from pipeline.storage import load_json, save_prompt
from pipeline.logging_setup import get_logger
from pipeline.config import LEVEL2_LOG_FILE

logger = get_logger("prompt_generator", LEVEL2_LOG_FILE)


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=LLM_FAST_MODEL,
        api_key=os.environ["OPENAI_API_KEY"],
        temperature=0,
    )


META_PROMPT_TEMPLATE = """You are preparing a Deep Research query about a securities exchange.
This prompt is fully self-contained — all necessary context is included below.

JURISDICTION CONTEXT (from prior Level 1 research):
{jurisdiction_card_json}

VENUE TO RESEARCH:
Name (English): {venue_name_english}
Name (Local): {venue_name_local}
Jurisdiction (English): {jurisdiction_en}
Market Type: {market_type}
Operator: {operator_name}

INSTRUMENT CLASSES IN SCOPE:
- Equities: ordinary shares, preference shares
- Bonds: corporate bonds, sovereign/government bonds, convertible bonds
- Funds: ETF, closed-end funds, REIT
- Depositary receipts

DEFINITIONS — insert these verbatim into the generated prompt under a "DEFINITIONS" heading:

DEFINITION — Trading Venue (= "venue"):
A market with its own regulatory framework and its own set of admission rules,
operated by a market operator. This is the primary structural unit of analysis.

CLASSIFICATION TEST — When to treat two parts of the same exchange as separate venues:
If they have DIFFERENT regulatory status (e.g., one is a Regulated Market and the
other is an MTF), OR they have SEPARATE rulebooks governing admission, OR the type
of required intermediary differs (e.g., Sponsor vs. Nominated Adviser) — treat them
as separate venues.
If they share the SAME rulebook and the SAME regulatory status, but differ in the
STRICTNESS of quantitative thresholds — they are tiers within one venue, not
separate venues.

DEFINITION — Listing Tier:
A hierarchical level within a single venue that determines the strictness of
admission and continuing obligation requirements. A tier shares the SAME regulatory
framework and rulebook as other tiers, but sets HIGHER or LOWER quantitative
thresholds. If the entity has its OWN rulebook or DIFFERENT regulatory status — it
is a separate venue, not a tier.

DEFINITION — Specialized Segment:
A thematic or sectoral subdivision within a venue, with ADDITIONAL criteria on top
of the venue's base requirements. Does NOT replace base requirements — adds to them.
If the entity imposes thematically specific requirements (industry sector, ESG,
size category) rather than a general hierarchy of strictness — it is a segment.

DEFINITION — Admission Regime Modifier:
A set of rule modifications for a specific TYPE of issuer or instrument, without
creating a separate venue, tier, or segment. Changes WHO is eligible, not WHERE
the issuer is listed. Examples: HKEX Chapter 18A (Biotech), Chapter 18B (SPAC),
Chapter 8A (WVR), Nasdaq IM-5101-2 (SPAC-specific standards).
Do NOT classify modifiers as tiers or segments. List them separately.

VALIDATION CHECKS — insert these verbatim into the generated prompt under a "VALIDATION CHECKS"
heading, instructing the researcher to apply them before finalising the structure:

1. VENUE vs TIER: For each entity classified as a "tier" — does it have its OWN
   rulebook separate from this venue's rulebook? If yes → it is a separate venue,
   not a tier. Do NOT include it as a tier of this venue.

2. TIER vs SEGMENT: For each entity classified as a "tier" — are requirements a
   stricter/looser version of another tier (vertical hierarchy)? If instead they
   are thematically specific (sectoral, ESG, size-based) — reclassify as a segment.

3. SEGMENT vs MODIFIER: For each entity classified as a "segment" — does it have
   its own named market place where issuers are listed? Or is it a rule adjustment
   for a specific issuer type? If the latter — reclassify as a regime_modifier.

Generate a Deep Research prompt in English that asks about the detailed
listing structure of {venue_name_english}, a {market_type} operated by {operator_name}.
The prompt must:

1. Open with: "Research the detailed listing structure of {venue_name_english},
   a {market_type} operated by {operator_name}."
2. Include verbatim the DEFINITIONS block above under a "DEFINITIONS" heading.
3. Include verbatim the VALIDATION CHECKS block above under a "VALIDATION CHECKS"
   heading, instructing the researcher to apply them before finalising the structure.
4. Use the exact local terminology for tiers, segments, and rulebook
   sections (from the jurisdiction context above — key_terms_mapping,
   venues list, admission_architecture).
5. Cover for each tier/board separately:
   a) Which instrument classes are admitted (from the scope above only)
   b) Sub-segments if any
   c) Whether there is a separate issuer eligibility process vs per-issue admission
   d) Secondary/dual listing regime (if applicable): which chapter of rulebook,
      eligibility criteria, what standard requirements are modified
   e) Specific rulebook chapters governing each instrument class
6. Be self-contained — include all necessary context within the prompt itself
   (regulator name, venue type, key rulebook names from the jurisdiction card).
7. Ask for specific rule/chapter references throughout.

Return ONLY the generated Deep Research prompt text, nothing else.
"""


def _build_meta_prompt(venue: dict) -> str:
    """
    Build the meta-prompt string for a single venue WITHOUT calling the LLM.

    Loads jurisdiction_card.json and formats META_PROMPT_TEMPLATE.
    Raises FileNotFoundError if the jurisdiction card is missing.
    """
    name_ru = venue["name_ru"]
    name_en = venue["name_en"]
    venue_name_english = venue["venue_name_english"]
    venue_name_local = venue["venue_name_local"]
    market_type = venue.get("market_type", "")
    operator_name = venue.get("operator_name_en", "")

    card_path = get_country_level1_dir(name_ru) / "jurisdiction_card.json"
    card_data = load_json(card_path)
    if card_data is None:
        raise FileNotFoundError(
            f"jurisdiction_card.json not found for {name_ru} at {card_path}. "
            "Run Level 1 postprocessing first."
        )

    jurisdiction_card_json = json.dumps(card_data, ensure_ascii=False, indent=2)

    return META_PROMPT_TEMPLATE.format(
        jurisdiction_card_json=jurisdiction_card_json,
        venue_name_english=venue_name_english,
        venue_name_local=venue_name_local,
        jurisdiction_en=name_en,
        market_type=market_type,
        operator_name=operator_name,
    )


def generate_prompt_for_venue(venue: dict) -> str:
    """
    Generate a 2A Deep Research prompt for a single venue.

    venue: dict with keys venue_key, name_ru, name_en, venue_name_english,
           venue_name_local, and optionally market_type, operator_name_en.
    Returns: the generated prompt text
    """
    venue_key = venue["venue_key"]
    meta_prompt = _build_meta_prompt(venue)

    logger.info("Generating 2A prompt for venue: %s", venue_key)
    llm = _get_llm()
    result = llm.invoke(meta_prompt)
    generated_prompt = result.content.strip()

    logger.info("Generated 2A prompt for %s (%d chars)", venue_key, len(generated_prompt))
    return generated_prompt


def generate_all_prompts(venues: list = None) -> dict[str, str]:
    """
    Generate 2A prompts for all PILOT_VENUES using llm.batch() for parallelism.
    Saves each prompt to 03_data/prompts/level_2/{venue_key}_prompt.txt.
    Returns dict of {venue_key: prompt_text}.

    Idempotent: venues whose prompt already exists on disk are loaded and skipped.
    """
    # Phase 1: load existing prompts from disk; collect venues that need generation
    prompts: dict[str, str] = {}
    venues_to_generate = []
    meta_prompts = []

    for venue in (venues or PILOT_VENUES):
        venue_key = venue["venue_key"]
        prompt_path = PROMPTS_LEVEL2_DIR / f"{venue_key}_prompt.txt"
        if prompt_path.exists():
            logger.info("Prompt for %s already exists, loading from disk.", venue_key)
            with open(prompt_path, encoding="utf-8") as f:
                prompts[venue_key] = f.read()
        else:
            meta_prompt = _build_meta_prompt(venue)
            venues_to_generate.append(venue)
            meta_prompts.append(meta_prompt)

    if not venues_to_generate:
        logger.info("All prompts already exist — nothing to generate.")
        return prompts

    logger.info(
        "Batching %d prompt generation call(s) (max_concurrency=50)...",
        len(venues_to_generate),
    )

    # Phase 2: single batch call
    llm = _get_llm()
    results = llm.batch(meta_prompts, config={"max_concurrency": 50})

    # Phase 3: save results
    for venue, result in zip(venues_to_generate, results):
        venue_key = venue["venue_key"]
        try:
            generated_prompt = result.content.strip()
            save_prompt(PROMPTS_LEVEL2_DIR, f"{venue_key}_prompt", generated_prompt)
            prompts[venue_key] = generated_prompt
            logger.info("Saved prompt for %s (%d chars)", venue_key, len(generated_prompt))
        except Exception as e:
            logger.error("Failed to save prompt for %s: %s", venue_key, e)
            prompts[venue_key] = None

    return prompts


if __name__ == "__main__":
    generate_all_prompts()
