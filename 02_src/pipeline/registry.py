"""
Registry helpers: load jurisdictions from registry, discover venues from L1 outputs.
"""
import json
import re
from pathlib import Path
from typing import Optional

# Path to jurisdictions registry (relative to project root)
_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "03_data" / "jurisdictions_registry.json"


def load_jurisdictions(registry_path: Optional[Path] = None) -> list[dict]:
    """
    Load full jurisdiction list from jurisdictions_registry.json.
    Returns list of dicts: {name_ru, name_en, market_group, eu_member, eu_note}.
    """
    path = registry_path or _REGISTRY_PATH
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_jurisdiction(name_ru: str = None, name_en: str = None,
                     registry_path: Optional[Path] = None) -> Optional[dict]:
    """
    Find jurisdiction by Russian or English name.
    Returns None if not found.
    """
    jurisdictions = load_jurisdictions(registry_path)
    for j in jurisdictions:
        if name_ru and j["name_ru"] == name_ru:
            return j
        if name_en and j["name_en"] == name_en:
            return j
    return None


def slugify_venue_name(name: str) -> str:
    """
    Convert a venue English name to a venue_key string.

    Examples:
      "HKEX Main Board"                        → "HKEX_Main_Board"
      "HKEX GEM (Growth Enterprise Market)"    → "HKEX_GEM"
      "London Stock Exchange – Main Market"    → "London_Stock_Exchange_Main_Market"
      "Aquis Stock Exchange – Growth Market"   → "Aquis_Stock_Exchange_Growth_Market"
      "Tradeweb UK OTF"                        → "Tradeweb_UK_OTF"
    """
    # Remove parenthetical suffixes like "(Growth Enterprise Market)"
    name = re.sub(r'\s*\([^)]*\)', '', name)
    # Replace em-dash, en-dash, hyphen used as separator → space
    name = re.sub(r'\s*[–—]\s*', ' ', name)
    # Remove remaining special characters except alphanumerics and spaces
    name = re.sub(r'[^\w\s]', '', name)
    # Replace whitespace runs with single underscore
    name = re.sub(r'\s+', '_', name.strip())
    # Collapse consecutive underscores
    name = re.sub(r'_+', '_', name)
    return name.strip('_')


def _normalize_market_type(raw_type: str) -> str:
    """
    Normalize venue type string from venues_list.json to consistent market_type value.

    "Regulated Market"              → "regulated_market"
    "Multilateral Trading Facility" → "MTF"
    "Organised Trading Facility"    → "OTF"
    other                           → raw_type (lowercased, underscored)
    """
    mapping = {
        "regulated market": "regulated_market",
        "multilateral trading facility": "MTF",
        "organised trading facility": "OTF",
        "organized trading facility": "OTF",
    }
    return mapping.get(raw_type.strip().lower(), raw_type.strip().replace(' ', '_').lower())


def discover_venues_for_jurisdiction(
    name_ru: str,
    name_en: str,
    countries_dir: Path,
) -> list[dict]:
    """
    Build venue config list for a jurisdiction from existing L2 data or L1 outputs.

    Priority:
      1. If level_2/ contains venue_card.json files → build configs from those.
         This handles backward compatibility: existing venue_keys match state file entries.
      2. Otherwise, read level_1/venues_list.json and slugify venue names → new venue_keys.

    Returns list of venue config dicts compatible with PILOT_VENUES format:
      {venue_key, name_ru, name_en, venue_name_english, venue_name_local,
       market_type, operator_key, operator_name_en}
    """
    # --- Priority 1: existing venue_card.json files in level_2/ ---
    level2_dir = countries_dir / name_ru / "level_2"
    if level2_dir.exists():
        existing_venues = []
        for venue_dir in sorted(level2_dir.iterdir()):
            if not venue_dir.is_dir():
                continue
            card_path = venue_dir / "venue_card.json"
            if not card_path.exists():
                continue
            try:
                with open(card_path, encoding="utf-8") as f:
                    card = json.load(f)
                venue_key = card.get("venue_key") or venue_dir.name
                existing_venues.append({
                    "venue_key": venue_key,
                    "operator_key": "",
                    "operator_name_en": card.get("operator", ""),
                    "name_en": name_en,
                    "name_ru": name_ru,
                    "venue_name_english": card.get("venue_name_english", ""),
                    "venue_name_local": card.get("venue_name_local", ""),
                    "market_type": _normalize_market_type(card.get("venue_type", "")),
                })
            except Exception:
                pass
        if existing_venues:
            return existing_venues

    # --- Priority 2: derive from level_1/venues_list.json ---
    venues_list_path = countries_dir / name_ru / "level_1" / "venues_list.json"
    if not venues_list_path.exists():
        return []

    with open(venues_list_path, encoding="utf-8") as f:
        data = json.load(f)

    raw_venues = data.get("venues", [])
    if not raw_venues:
        return []

    venue_configs = []
    for v in raw_venues:
        venue_name_english = v.get("name_english", "")
        if not venue_name_english:
            continue

        venue_key = slugify_venue_name(venue_name_english)

        venue_configs.append({
            "venue_key": venue_key,
            "operator_key": "",
            "operator_name_en": "",
            "name_en": name_en,
            "name_ru": name_ru,
            "venue_name_english": venue_name_english,
            "venue_name_local": v.get("name_local", venue_name_english),
            "market_type": _normalize_market_type(v.get("type", "")),
        })

    return venue_configs


def discover_all_venues(
    jurisdictions: list[dict],
    countries_dir: Path,
) -> list[dict]:
    """
    Discover venues for a list of jurisdictions.
    Returns flat list of venue configs (same format as PILOT_VENUES).
    """
    all_venues = []
    for j in jurisdictions:
        venues = discover_venues_for_jurisdiction(
            name_ru=j["name_ru"],
            name_en=j["name_en"],
            countries_dir=countries_dir,
        )
        all_venues.extend(venues)
    return all_venues
