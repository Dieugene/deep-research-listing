"""
LLM postprocessor using Langchain + OpenAI.

Uses .with_structured_output(PydanticModel) for structured extraction.
All prompts are self-contained — no reliance on dialog context.
"""
import os
import json
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from pipeline.config import LLM_SMART_MODEL, LLM_FAST_MODEL, DATA_DIR
from pipeline.logging_setup import get_logger

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

logger = get_logger("llm_postprocessor")

EXCHANGES_PATH = DATA_DIR / "exchanges.json"


def _load_mandatory_primary(jurisdiction_ru: str) -> list[str]:
    """Load curated venue names from exchanges.json for a jurisdiction."""
    if not EXCHANGES_PATH.exists():
        return []
    try:
        data = json.loads(EXCHANGES_PATH.read_text(encoding="utf-8"))
        for group in data.values():  # DM / EM
            if jurisdiction_ru in group:
                return list(group[jurisdiction_ru].keys())
        return []
    except Exception:
        return []


def _get_llm(model: str = LLM_SMART_MODEL) -> ChatOpenAI:
    """Create a ChatOpenAI instance using env vars."""
    return ChatOpenAI(
        model=model,
        api_key=os.environ["OPENAI_API_KEY"],
        temperature=0,
    )


# ---------------------------------------------------------------------------
# Pydantic models for structured output
# ---------------------------------------------------------------------------

class VenueRef(BaseModel):
    name_english: str
    name_local: str
    type: str
    tiers: list[str]
    research_priority: str = "primary"  # "primary" or "deferred"


class ExcludedVenueRef(BaseModel):
    name: str
    reason: str


class JurisdictionCard(BaseModel):
    jurisdiction: str
    jurisdiction_ru: str
    legal_family: str
    regulator_name: str
    regulator_type: str
    admission_architecture: str
    admission_architecture_ru: str
    listing_authority: str
    market_types: list[str]
    key_terms_mapping: Optional[dict[str, str]] = None
    venues: list[VenueRef]
    excluded_venues: list[ExcludedVenueRef] = Field(default_factory=list)
    supranational_flag: bool
    supranational_framework: Optional[str] = None
    notes: str


# ---------------------------------------------------------------------------
# Postprocessing entry point
# ---------------------------------------------------------------------------

def build_jurisdiction_card(
    jurisdiction_en: str,
    jurisdiction_ru: str,
    content_1a: str,
    content_1b,
    content_1c,
) -> JurisdictionCard:
    """
    Build a JurisdictionCard from raw research outputs 1A, 1B, 1C.

    content_1a: str (text output)
    content_1b: dict or str (JSON output from 1B)
    content_1c: dict or str (JSON output from 1C)
    """
    # Serialize 1B and 1C to strings if they are dicts
    def _to_str(v) -> str:
        if isinstance(v, dict):
            return json.dumps(v, ensure_ascii=False, indent=2)
        return str(v)

    content_1b_str = _to_str(content_1b)
    content_1c_str = _to_str(content_1c)

    # Build mandatory primary block from exchanges.json
    mandatory_venues = _load_mandatory_primary(jurisdiction_ru)
    if mandatory_venues:
        venue_lines = "\n".join(f"   - {v.replace('_', ' ')}" for v in mandatory_venues)
        mandatory_primary_block = (
            "\n"
            "   Step 4 (ADDITIONAL CONSTRAINT): The following venues come from a curated\n"
            "   reference list and MUST be \"primary\" even if Steps 1-2 would mark them\n"
            "   as \"deferred\". Apply Steps 1-3 as normal for ALL other venues first,\n"
            "   then override these specific venues to \"primary\" if they were marked\n"
            "   \"deferred\":\n"
            f"{venue_lines}\n"
        )
    else:
        mandatory_primary_block = ""

    prompt = f"""You are processing research results about {jurisdiction_en} securities markets.
All necessary information is provided below — this prompt is fully self-contained.

Below are three research outputs:

--- 1A: REGULATORY ARCHITECTURE ---
{content_1a}

--- 1B: INSTITUTIONAL FACTORS ---
{content_1b_str}

--- 1C: VENUE LANDSCAPE ---
{content_1c_str}

Your tasks:
1. Create a structured jurisdiction card combining all three sources.
2. Translate key descriptive fields to Russian (jurisdiction_ru, admission_architecture_ru).
3. Extract a list of venues for further research (Level 2). BEFORE including any venue, verify ALL four conditions:

   VERIFICATION CHECKS — include a venue ONLY if it passes all four:
   1. DOMICILED in {jurisdiction_en} — operated by an entity registered and regulated
      in this jurisdiction. Foreign venues mentioned in cross-listing context → EXCLUDE.
   2. ADMITS at least one of: equities, bonds, investment funds (ETF/REIT/closed-end), or
      depositary receipts. Crypto/commodity/derivatives-only venues → EXCLUDE.
   3. HAS FORMAL ADMISSION PROCEDURES — a defined process for admitting issuers/instruments
      with published rules. Execution venues / dark pools / SIs without issuer admission → EXCLUDE.
   4. CURRENTLY OPERATIONAL — valid license, actively operating. Ceased or revoked → EXCLUDE.

   For each venue that passes: include in `venues` with name_english, name_local, type, tiers.
   For each venue that FAILS any check: include in `excluded_venues` with name and reason
   (e.g., "excluded: foreign venue, cross-listing reference" or
   "excluded: no formal admission procedures (dark pool)").
4. Set supranational_flag=true ONLY if a supranational legislative framework directly governs listing/admission to trading requirements in this jurisdiction (e.g., EU Prospectus Regulation, MiFID II for EU member states). Do NOT set supranational_flag=true for: cross-border investor access schemes (Stock Connect, Bond Connect, etc.); mutual recognition arrangements for investment products; international standards (IOSCO principles) that are not binding legislation; any arrangement that affects who can invest, not what is required for listing. If such a supranational framework exists, name it in supranational_framework.
5. RESEARCH PRIORITY — for each included venue, assign research_priority:

   Step 1: Group venues by their type/regulatory_status (e.g., all "Regulated Market" venues together, all "MTF" together, all "Freiverkehr" together).

   Step 2: For each group:
   - If the group contains exactly ONE venue -> "primary"
   - If the group contains MULTIPLE venues -> select the ONE most significant venue as "primary", mark the rest as "deferred"

   Criteria for selecting primary (apply in order, use the first that distinguishes):
   - Explicitly described as "main", "largest", "leading", "principal" in the source data
   - Has the most complex structure (more tiers, segments, instrument classes)
   - Is located in the financial capital of the jurisdiction
   - Is mentioned first or most prominently in the regulatory overview (1A data)

   Step 3: Venues with a UNIQUE type/regulatory_status (no other venue shares it) -> always "primary".
{mandatory_primary_block}
   Record research_priority: "primary" or "deferred" for each venue in the venues array.
6. Fill key_terms_mapping with local official terms mapped to their English equivalents (at least 5-10 key terms).
7. Be precise about legal_family (common law / civil law / mixed / other).
8. For regulator_type use: central bank / commission / supranational / other.
9. For admission_architecture describe whether official listing and admission to trading are unified or separate concepts.

Return valid JSON matching the required schema. All fields must be populated.
Jurisdiction (English): {jurisdiction_en}
Jurisdiction (Russian): {jurisdiction_ru}
"""

    logger.info("Running LLM postprocessing for %s", jurisdiction_en)
    llm = _get_llm(LLM_SMART_MODEL)
    # Use method="function_calling" for broader schema compatibility
    # (dict fields are not supported by strict JSON schema mode)
    chain = llm.with_structured_output(JurisdictionCard, method="function_calling")
    card: JurisdictionCard = chain.invoke(prompt)
    logger.info("LLM postprocessing complete for %s", jurisdiction_en)
    return card


def build_venues_list(card: JurisdictionCard) -> list[dict]:
    """Extract a venues list dict from the card, ready to save as venues_list.json."""
    return [v.model_dump() for v in card.venues]
