"""
Import institutional factors (1B) from a pre-collected MD file.

Replaces the Parallel Deep Research 1B query for pilot jurisdictions
by extracting structured data from pilot_jurisdiction_cards.md using
LangChain + gpt-5-mini structured output.

Usage:
    python -m level_1.import_institutional
    python -m level_1.import_institutional --md-file /path/to/file.md
"""
import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from pipeline.config import PILOT_JURISDICTIONS, get_country_level1_dir
from pipeline.storage import save_json
from pipeline.logging_setup import get_logger

logger = get_logger("import_institutional")

# ---------------------------------------------------------------------------
# Default MD source file
# ---------------------------------------------------------------------------

DEFAULT_MD_FILE = Path(
    r"D:\_storage_cbr\040_listing_deep_research\03_institutional_factors"
    r"\_pilot_results\pilot_jurisdiction_cards.md"
)

# ---------------------------------------------------------------------------
# Pydantic models for structured output
# ---------------------------------------------------------------------------


class FactorWithAssessment(BaseModel):
    value: str = Field(description="Short categorical value")
    assessment: str = Field(description="Substantive explanation / reasoning")
    source: str = Field(description="Source reference(s)")


class F8OwnershipConcentration(BaseModel):
    value: str = Field(description="Short categorical value (e.g. 'дисперсная', 'высокая')")
    state_share_pct: str = Field(
        description="State share percentage if available, else empty string or 'н/д'"
    )
    assessment: str = Field(description="Substantive explanation / reasoning")
    source: str = Field(description="Source reference(s)")


class F9InvestorBase(BaseModel):
    value: str = Field(
        description="Short categorical value (e.g. 'институционалы', 'розница', 'смешанная')"
    )
    institutional_share_pct: str = Field(
        description="Institutional share percentage if available, else empty string or 'н/д'"
    )
    source: str = Field(description="Source reference(s)")


class PreloadedFactor(BaseModel):
    confirmed: bool = Field(description="Whether the pre-loaded value is confirmed")
    corrected_value: Optional[str] = Field(
        default=None,
        description="Corrected value if confirmed=False, else null",
    )
    value: str = Field(description="The actual value (pre-loaded or corrected)")
    source: str = Field(description="Source reference(s)")


class InstitutionalFactors(BaseModel):
    """Structured extraction of institutional factors for one jurisdiction."""

    # Qualitative factors
    F3_private_enforcement: FactorWithAssessment = Field(
        description="Private enforcement level and details (F3)"
    )
    F8_ownership_concentration: F8OwnershipConcentration = Field(
        description="Ownership concentration level and details (F8)"
    )
    F9_investor_base: F9InvestorBase = Field(
        description="Investor base structure (F9)"
    )
    F12_exchange_as_sro: FactorWithAssessment = Field(
        description="Exchange SRO role (F12)"
    )

    # Preloaded verification
    F1_legal_family: PreloadedFactor = Field(
        description="Legal family verification (F1)"
    )
    F11_regulator_type: PreloadedFactor = Field(
        description="Regulator type verification (F11)"
    )

    # Additional factors
    F10_market_competition: FactorWithAssessment = Field(
        description="Market / venue competition structure (F10)"
    )


# ---------------------------------------------------------------------------
# MD parsing: extract per-jurisdiction blocks
# ---------------------------------------------------------------------------

# Map from English name to section headings that appear in the MD
JURISDICTION_HEADINGS = {
    "United Kingdom": ["United Kingdom"],
    "Hong Kong": ["Hong Kong"],
    "Russia": ["Russia"],
}


def extract_md_block(md_text: str, jurisdiction_en: str) -> str:
    """
    Extract the markdown section for the given jurisdiction.
    Returns the text from the ## heading up to the next ## heading (or end of file).
    """
    headings = JURISDICTION_HEADINGS.get(jurisdiction_en, [jurisdiction_en])
    for heading in headings:
        # Match ## <heading> (possibly with extra whitespace)
        pattern = rf"^##\s+{re.escape(heading)}\s*$"
        match = re.search(pattern, md_text, flags=re.MULTILINE | re.IGNORECASE)
        if match:
            start = match.start()
            # Find next ## section
            next_match = re.search(r"^##\s+", md_text[match.end():], flags=re.MULTILINE)
            if next_match:
                end = match.end() + next_match.start()
            else:
                end = len(md_text)
            return md_text[start:end].strip()
    raise ValueError(
        f"Could not find section for jurisdiction '{jurisdiction_en}' in MD file. "
        f"Tried headings: {headings}"
    )


# ---------------------------------------------------------------------------
# LLM extraction
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT_TEMPLATE = """\
You are a structured data extractor. Below is a research block about the \
securities market institutional factors for jurisdiction: {jurisdiction}.

Extract the following factors exactly as described in the text. \
Preserve original language for values and assessments (Russian is fine). \
If a specific data point is missing or uncertain, note that in the field. \
Do NOT invent data — only use what is explicitly stated or clearly implied.

RESEARCH BLOCK:
---
{md_block}
---

Extract all required fields from the block above.
"""


def extract_factors_for_jurisdiction(
    jurisdiction_en: str,
    md_block: str,
    llm: ChatOpenAI,
) -> InstitutionalFactors:
    """Use LLM structured output to extract factors from the MD block."""
    structured_llm = llm.with_structured_output(InstitutionalFactors, method="function_calling")
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(
        jurisdiction=jurisdiction_en,
        md_block=md_block,
    )
    logger.info("Calling LLM for %s (block length: %d chars)", jurisdiction_en, len(md_block))
    result: InstitutionalFactors = structured_llm.invoke(prompt)
    return result


# ---------------------------------------------------------------------------
# Build output JSON
# ---------------------------------------------------------------------------

def build_output_json(
    jurisdiction_en: str,
    factors: InstitutionalFactors,
    md_file_path: Path,
) -> dict:
    """Convert Pydantic model to the target JSON envelope format."""
    return {
        "jurisdiction": jurisdiction_en,
        "source": "import_from_md",
        "source_file": str(md_file_path.resolve()),
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "qualitative_factors": {
            "F3_private_enforcement": factors.F3_private_enforcement.model_dump(),
            "F8_ownership_concentration": factors.F8_ownership_concentration.model_dump(),
            "F9_investor_base": factors.F9_investor_base.model_dump(),
            "F12_exchange_as_sro": factors.F12_exchange_as_sro.model_dump(),
        },
        "preloaded_verification": {
            "F1_legal_family": factors.F1_legal_family.model_dump(),
            "F11_regulator_type": factors.F11_regulator_type.model_dump(),
        },
        "additional_factors": {
            "F10_market_competition": factors.F10_market_competition.model_dump(),
        },
    }


# ---------------------------------------------------------------------------
# Main import function
# ---------------------------------------------------------------------------

def import_all(md_file: Path = DEFAULT_MD_FILE) -> None:
    """
    Read the MD file, extract institutional factors for all pilot jurisdictions,
    and save each as 03_data/countries/{name_ru}/level_1/1B_institutional.json.
    """
    if not md_file.exists():
        raise FileNotFoundError(f"MD source file not found: {md_file}")

    md_text = md_file.read_text(encoding="utf-8")
    logger.info("Loaded MD file: %s (%d chars)", md_file, len(md_text))

    # Init LLM
    api_key = os.environ.get("OPENAI_API_KEY", "")
    llm = ChatOpenAI(
        model="gpt-5-mini",
        api_key=api_key,
        temperature=0,
    )

    for j in PILOT_JURISDICTIONS:
        en = j["name_en"]
        ru = j["name_ru"]
        logger.info("Processing jurisdiction: %s (%s)", en, ru)

        try:
            md_block = extract_md_block(md_text, en)
        except ValueError as exc:
            logger.error("Skipping %s: %s", en, exc)
            continue

        try:
            factors = extract_factors_for_jurisdiction(en, md_block, llm)
        except Exception as exc:
            logger.error("LLM extraction failed for %s: %s", en, exc)
            raise

        output = build_output_json(en, factors, md_file)

        dest_dir = get_country_level1_dir(ru)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / "1B_institutional.json"
        save_json(dest_path, output)
        logger.info("Saved: %s", dest_path)

    logger.info("Import complete.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import institutional factors (1B) from pre-collected MD file"
    )
    parser.add_argument(
        "--md-file",
        type=Path,
        default=DEFAULT_MD_FILE,
        help="Path to pilot_jurisdiction_cards.md",
    )
    args = parser.parse_args()
    import_all(md_file=args.md_file)
