"""
Level 1: LLM postprocessing — builds jurisdiction_card.json and venues_list.json.

Reads 1A, 1B, 1C for each pilot jurisdiction and calls LLM postprocessor.

Usage:
    python -m level_1.postprocess                    # process all jurisdictions
    python -m level_1.postprocess --jurisdiction UK  # process one (English name prefix)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.config import PILOT_JURISDICTIONS, get_country_level1_dir
from pipeline.storage import save_json, load_json
from pipeline.logging_setup import get_logger
from pipeline.llm_postprocessor import build_jurisdiction_card, build_venues_list

logger = get_logger("postprocess")


def _load_content(path: Path):
    """Load content from a raw Parallel output file. Handles both old and new formats."""
    data = load_json(path)
    if data is None:
        return None
    if not isinstance(data, dict):
        return data
    # New format: parallel_output.content
    if "parallel_output" in data:
        content = data["parallel_output"].get("content")
        if isinstance(content, str):
            try:
                return json.loads(content)
            except (json.JSONDecodeError, ValueError):
                return content
        return content
    # Old format: "content" key at top level
    if "content" in data:
        content = data["content"]
        if isinstance(content, str):
            try:
                return json.loads(content)
            except (json.JSONDecodeError, ValueError):
                return content
        return content
    # Really old format: content spread at top level (1B/1C old format)
    # Return the whole dict minus metadata keys
    return {k: v for k, v in data.items() if k not in ("jurisdiction", "retrieved_at", "query")}


def process_jurisdiction(juris_en: str, juris_ru: str) -> bool:
    """
    Run LLM postprocessing for one jurisdiction.
    Returns True on success, False if inputs are missing.
    """
    d = get_country_level1_dir(juris_ru)

    path_1a = d / "1A_architecture.json"
    path_1b = d / "1B_institutional.json"
    path_1c = d / "1C_venues.json"

    # Check all inputs exist
    missing = [p.name for p in [path_1a, path_1b, path_1c] if not p.exists()]
    if missing:
        logger.warning(
            "Skipping postprocessing for %s: missing files %s",
            juris_ru,
            missing,
        )
        return False

    # Check if already done
    card_path = d / "jurisdiction_card.json"
    venues_path = d / "venues_list.json"
    if card_path.exists() and venues_path.exists():
        logger.info("Postprocessing for %s already done, skipping.", juris_ru)
        return True

    logger.info("Postprocessing %s ...", juris_ru)

    # Load contents
    text_1a_raw = load_json(path_1a)
    if isinstance(text_1a_raw, dict):
        if "parallel_output" in text_1a_raw:
            text_1a = text_1a_raw["parallel_output"].get("content", "") or ""
        else:
            text_1a = text_1a_raw.get("content", json.dumps(text_1a_raw, ensure_ascii=False))
    else:
        text_1a = str(text_1a_raw) if text_1a_raw else ""

    content_1b = _load_content(path_1b)
    content_1c = _load_content(path_1c)

    try:
        card = build_jurisdiction_card(
            jurisdiction_en=juris_en,
            jurisdiction_ru=juris_ru,
            content_1a=text_1a,
            content_1b=content_1b,
            content_1c=content_1c,
        )
    except Exception as e:
        logger.error("LLM postprocessing failed for %s: %s", juris_ru, e)
        return False

    # Save jurisdiction_card.json
    save_json(card_path, card.model_dump())
    logger.info("Saved jurisdiction_card.json for %s", juris_ru)

    # Save venues_list.json
    venues = build_venues_list(card)
    save_json(venues_path, {"jurisdiction": juris_en, "venues": venues})
    logger.info("Saved venues_list.json for %s (%d venues)", juris_ru, len(venues))

    return True


def process_all(jurisdictions: list = None):
    """Run postprocessing for all pilot jurisdictions."""
    results = {}
    for j in (jurisdictions or PILOT_JURISDICTIONS):
        ok = process_jurisdiction(j["name_en"], j["name_ru"])
        results[j["name_ru"]] = "done" if ok else "skipped/failed"

    logger.info("=== Postprocessing summary ===")
    for name, status in results.items():
        logger.info("  %s: %s", name, status)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Level 1 LLM postprocessor")
    parser.add_argument(
        "--jurisdiction",
        type=str,
        default=None,
        help="English name (or prefix) of jurisdiction to process. If omitted, process all.",
    )
    args = parser.parse_args()

    if args.jurisdiction:
        # Find matching jurisdiction
        matches = [
            j for j in PILOT_JURISDICTIONS
            if j["name_en"].lower().startswith(args.jurisdiction.lower())
        ]
        if not matches:
            logger.error("No jurisdiction matching '%s'", args.jurisdiction)
            sys.exit(1)
        for j in matches:
            process_jurisdiction(j["name_en"], j["name_ru"])
    else:
        process_all()
