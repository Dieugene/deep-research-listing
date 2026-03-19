"""
Task 012: L1/L2 field normalizations.
Adds/normalizes: legal_family, market_type, listing_authority_short (L1)
                 venue_type (L2)
"""
import json
import os
import datetime
import tempfile
from pathlib import Path

from pipeline.config import COUNTRIES_DIR, LOGS_DIR, LLM_FAST_MODEL
from pipeline.logging_setup import get_logger

logger = get_logger(
    "l1_l2_normalize",
    LOGS_DIR / f"l1_l2_normalize_{datetime.date.today()}.log"
)

_LEGAL_FAMILY_VALID = {"common law", "civil law", "mixed"}

_MARKET_TYPE_LOOKUP = {
    "Австралия": "DM",
    "Великобритания": "DM",
    "Германия": "DM",
    "Гонконг": "DM",
    "Сингапур": "DM",
    "Франция": "DM",
}

_VENUE_TYPE_MAP = {
    "MTF": "mtf",
    "OTF": "otf",
    "other": "exchange_regulated",  # German Freiverkehr venues
}

_VENUE_TYPE_NORMALIZED = {"regulated_market", "mtf", "otf", "exchange_regulated"}


def _load_json(path: Path) -> dict | None:
    """Load JSON from path, returning None on error."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("File not found: %s", path)
        return None
    except json.JSONDecodeError as exc:
        logger.error("JSON decode error in %s: %s", path, exc)
        return None


def _save_json(path: Path, data: dict) -> None:
    """Atomically write JSON to path (temp file + os.replace)."""
    content = json.dumps(data, ensure_ascii=False, indent=2)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _normalize_legal_family(val: str) -> str | None:
    """
    Normalize legal_family to lowercase.
    Returns the normalized value if it is valid, else None.
    """
    if not isinstance(val, str) or not val.strip():
        return None
    normalized = val.strip().lower()
    if normalized in _LEGAL_FAMILY_VALID:
        return normalized
    return None


def _get_listing_authority_short(listing_authority: str, llm) -> str | None:
    """
    Use LLM to extract a short abbreviation/name (max 30 chars) for listing_authority.
    Returns the short name string, or None on failure.
    """
    from langchain_core.messages import SystemMessage, HumanMessage

    system = SystemMessage(content=(
        "You are a financial regulatory expert. "
        "Extract a short abbreviation or name (max 30 characters) for the listing authority. "
        "Use the official acronym if visible in parentheses (e.g. FCA, SEHK, SGX-ST, AMF, ASIC). "
        "Return ONLY the short name, nothing else."
    ))
    human = HumanMessage(content=listing_authority)
    try:
        response = llm.invoke([system, human])
        short_name = response.content.strip()[:30]
        if not short_name:
            logger.warning("LLM returned empty content for listing_authority_short")
            return None
        return short_name
    except Exception as exc:
        logger.error("LLM call raised exception for listing_authority_short: %s", exc)
        return None


def process_l1_normalizations(
    jurisdictions: list[str] | None = None,
    llm=None
) -> None:
    """
    Normalize jurisdiction_card.json:
    - legal_family (algorithmic)
    - market_type (lookup, new field)
    - listing_authority_short (LLM, new field)
    Idempotent.
    jurisdictions: list of name_ru. None = process all.
    llm: langchain LLM instance. If None, created internally using LLM_FAST_MODEL.
    """
    if jurisdictions is None:
        # Discover all jurisdictions from COUNTRIES_DIR
        jurisdictions = [
            d.name for d in sorted(COUNTRIES_DIR.iterdir())
            if d.is_dir() and (d / "level_1" / "jurisdiction_card.json").exists()
        ]

    # Local LLM reference — created lazily on first need
    _llm = llm

    for name_ru in jurisdictions:
        card_path = COUNTRIES_DIR / name_ru / "level_1" / "jurisdiction_card.json"
        if not card_path.exists():
            logger.warning("[L1] jurisdiction_card.json not found for %s — skipping", name_ru)
            continue

        data = _load_json(card_path)
        if data is None:
            continue

        changed = False
        changes = []

        # --- С-1: legal_family normalization ---
        lf_raw = data.get("legal_family", "")
        if lf_raw:
            lf_normalized = _normalize_legal_family(lf_raw)
            if lf_normalized is None:
                logger.warning(
                    "[L1] %s — legal_family '%s' is not a known value, skipping normalization",
                    name_ru, lf_raw
                )
            elif lf_raw != lf_normalized:
                data["legal_family"] = lf_normalized
                changes.append(f"legal_family: '{lf_raw}' → '{lf_normalized}'")
                changed = True

        # --- С-2: market_type (new field) ---
        if "market_type" not in data:
            mt = _MARKET_TYPE_LOOKUP.get(name_ru)
            if mt is None:
                logger.warning(
                    "[L1] %s — not found in _MARKET_TYPE_LOOKUP, skipping market_type",
                    name_ru
                )
            else:
                data["market_type"] = mt
                changes.append(f"market_type: '{mt}'")
                changed = True

        # --- Ю-1: listing_authority_short (new field, LLM) ---
        if "listing_authority_short" not in data:
            la = data.get("listing_authority", "")
            if la:
                if _llm is None:
                    from langchain_openai import ChatOpenAI
                    _llm = ChatOpenAI(model=LLM_FAST_MODEL, temperature=0)
                short = _get_listing_authority_short(la, _llm)
                if short:
                    data["listing_authority_short"] = short
                    changes.append(f"listing_authority_short: '{short}'")
                    changed = True
                else:
                    logger.error(
                        "[L1] %s — listing_authority_short not obtained from LLM (empty or error)",
                        name_ru
                    )
            else:
                logger.warning(
                    "[L1] %s — listing_authority is empty/missing, skipping listing_authority_short",
                    name_ru
                )

        if changed:
            _save_json(card_path, data)
            logger.info("[L1 UPDATED] %s — %s", name_ru, ", ".join(changes))
        else:
            logger.info("[L1 SKIP] %s — already normalized", name_ru)


def process_l2_normalizations(
    jurisdictions: list[str] | None = None
) -> None:
    """
    Normalize venue_card.json venue_type.
    Idempotent.
    jurisdictions: list of name_ru. None = process all.
    """
    if jurisdictions is None:
        # Discover all jurisdictions that have a level_2 directory
        jurisdictions = [
            d.name for d in sorted(COUNTRIES_DIR.iterdir())
            if d.is_dir() and (d / "level_2").exists()
        ]

    for name_ru in jurisdictions:
        level2_dir = COUNTRIES_DIR / name_ru / "level_2"
        if not level2_dir.exists():
            logger.warning("[L2] level_2 dir not found for %s — skipping", name_ru)
            continue

        for venue_dir in sorted(level2_dir.iterdir()):
            if not venue_dir.is_dir():
                continue
            card_path = venue_dir / "venue_card.json"
            if not card_path.exists():
                continue

            data = _load_json(card_path)
            if data is None:
                continue

            venue_key = data.get("venue_key", venue_dir.name)
            vt_raw = data.get("venue_type", "")

            # Idempotent: skip if already normalized
            if vt_raw in _VENUE_TYPE_NORMALIZED:
                logger.info("[L2 SKIP] %s — already normalized", venue_key)
                continue

            if not vt_raw:
                logger.warning("[L2] %s — venue_type is missing/empty, skipping", venue_key)
                continue

            vt_new = _VENUE_TYPE_MAP.get(vt_raw)
            if vt_new is None:
                logger.warning(
                    "[L2] %s — venue_type '%s' not in _VENUE_TYPE_MAP, skipping",
                    venue_key, vt_raw
                )
                continue

            data["venue_type"] = vt_new
            _save_json(card_path, data)
            logger.info("[L2 UPDATED] %s — venue_type: '%s' → '%s'", venue_key, vt_raw, vt_new)
