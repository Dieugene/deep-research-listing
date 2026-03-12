"""
Pipeline configuration: constants, jurisdiction list, venue mappings.
"""
import json
import os
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).resolve().parents[2]

# Data directories
DATA_DIR = ROOT_DIR / "03_data"
LOGS_DIR = ROOT_DIR / "04_logs"

# Supranational data
SUPRANATIONAL_DIR = DATA_DIR / "supranational"

# Countries data
COUNTRIES_DIR = DATA_DIR / "countries"

# Prompts storage (for reproducibility)
PROMPTS_DIR = DATA_DIR / "prompts" / "level_1"
PROMPTS_LEVEL2_DIR = DATA_DIR / "prompts" / "level_2"
PROMPTS_LEVEL3_DIR = DATA_DIR / "prompts" / "level_3"

# State files for resumable execution
LEVEL1_STATE_FILE = LOGS_DIR / "level1_state.json"
LEVEL2_STATE_FILE = LOGS_DIR / "level2_state.json"

# Log files (date-stamped at runtime)
import datetime
_today = datetime.date.today().strftime("%Y%m%d")
LEVEL1_LOG_FILE = LOGS_DIR / f"level1_{_today}.log"
LEVEL2_LOG_FILE = LOGS_DIR / f"level2_{_today}.log"

# Parallel SDK processor to use
PARALLEL_PROCESSOR = "pro"

# Poll interval in seconds for Parallel task status
POLL_INTERVAL_SECONDS = 60

# LLM models
LLM_SMART_MODEL = "gpt-5"
LLM_FAST_MODEL = "gpt-5-mini"

# Pilot jurisdictions (English name for prompts, Russian name for storage)
PILOT_JURISDICTIONS = [
    {
        "name_en": "United Kingdom",
        "name_ru": "Великобритания",
        "eu_note": (
            "Note: UK left the EU in January 2020. "
            "Include references to retained EU law where relevant."
        ),
        "venues": ["LSE_Main_Market", "LSE_AIM", "Aquis_Stock_Exchange"],
    },
    {
        "name_en": "Hong Kong",
        "name_ru": "Гонконг",
        "eu_note": None,
        "venues": ["HKEX_Main_Board", "HKEX_GEM"],
    },
    {
        "name_en": "Russia",
        "name_ru": "Россия",
        "eu_note": None,
        "venues": ["МосБиржа"],
    },
]

# Map English name to jurisdiction config
JURISDICTION_BY_EN = {j["name_en"]: j for j in PILOT_JURISDICTIONS}
JURISDICTION_BY_RU = {j["name_ru"]: j for j in PILOT_JURISDICTIONS}


# Instrument classes in scope
INSTRUMENT_CLASSES = ["equity", "bond", "fund", "depositary_receipt"]

# Pilot venues for Level 2 (venue-level granularity: one entry per venue, not per operator)
PILOT_VENUES = [
    {
        "venue_key": "LSE_Main_Market",
        "operator_key": "LSE",
        "operator_name_en": "London Stock Exchange Group plc",
        "name_en": "United Kingdom",
        "name_ru": "Великобритания",
        "venue_name_english": "London Stock Exchange – Main Market",
        "venue_name_local": "London Stock Exchange – Main Market",
        "market_type": "regulated_market",
    },
    {
        "venue_key": "LSE_AIM",
        "operator_key": "LSE",
        "operator_name_en": "London Stock Exchange Group plc",
        "name_en": "United Kingdom",
        "name_ru": "Великобритания",
        "venue_name_english": "AIM (London Stock Exchange)",
        "venue_name_local": "AIM",
        "market_type": "MTF",
    },
    {
        "venue_key": "Aquis_Stock_Exchange",
        "operator_key": "Aquis",
        "operator_name_en": "Aquis Stock Exchange Limited",
        "name_en": "United Kingdom",
        "name_ru": "Великобритания",
        "venue_name_english": "Aquis Stock Exchange",
        "venue_name_local": "Aquis Stock Exchange",
        "market_type": "regulated_market",
    },
    {
        "venue_key": "HKEX_Main_Board",
        "operator_key": "HKEX",
        "operator_name_en": "Hong Kong Exchanges and Clearing Limited (HKEX)",
        "name_en": "Hong Kong",
        "name_ru": "Гонконг",
        "venue_name_english": "HKEX Main Board",
        "venue_name_local": "香港聯合交易所主板",
        "market_type": "regulated_market",
    },
    {
        "venue_key": "HKEX_GEM",
        "operator_key": "HKEX",
        "operator_name_en": "Hong Kong Exchanges and Clearing Limited (HKEX)",
        "name_en": "Hong Kong",
        "name_ru": "Гонконг",
        "venue_name_english": "HKEX GEM (Growth Enterprise Market)",
        "venue_name_local": "香港聯合交易所創業板 (GEM)",
        "market_type": "regulated_market",
    },
]

# Map venue_key to venue config
VENUE_BY_KEY = {v["venue_key"]: v for v in PILOT_VENUES}


def get_country_level1_dir(name_ru: str) -> Path:
    """Return path to level_1 data dir for a jurisdiction (Russian name)."""
    return COUNTRIES_DIR / name_ru / "level_1"


def get_country_level2_dir(name_ru: str, venue_key: str) -> Path:
    """Return path to level_2 data dir for a venue (Russian jurisdiction name, venue key)."""
    return COUNTRIES_DIR / name_ru / "level_2" / venue_key


def get_country_level3_dir(name_ru: str, venue_key: str) -> Path:
    """Return path to level_3 data dir for a venue."""
    return COUNTRIES_DIR / name_ru / "level_3" / venue_key


def get_country_level4_dir(name_ru: str) -> Path:
    """Return path to level_4 data dir for a jurisdiction."""
    return COUNTRIES_DIR / name_ru / "level_4"


LEVEL3_STATE_FILE = LOGS_DIR / "level3_state.json"
LEVEL3_LOG_FILE = LOGS_DIR / f"level3_{_today}.log"

LEVEL3_V2_STATE_FILE = LOGS_DIR / "level3_v2_state.json"
LEVEL3_V2_LOG_FILE = LOGS_DIR / f"level3_v2_{_today}.log"
PROMPTS_LEVEL3_V2_DIR = DATA_DIR / "prompts" / "level_3_v2"

PHASE2_STATE_FILE = LOGS_DIR / "phase2_state.json"
PHASE2_LOG_FILE = LOGS_DIR / f"phase2_{_today}.log"

LEVEL4_STATE_FILE = LOGS_DIR / "level4_state.json"
LEVEL4_LOG_FILE = LOGS_DIR / f"level4_{_today}.log"


def load_exchanges() -> dict:
    """Load the full exchanges.json."""
    path = DATA_DIR / "exchanges.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)
