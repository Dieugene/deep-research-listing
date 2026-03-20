"""
Top-level pipeline orchestrator.

Runs L1 → L2 → L3 → Phase 2 → L4 for a batch of jurisdictions.

Usage:
    python run_pipeline.py --jurisdictions Австралия Германия
    python run_pipeline.py --batch 10 --offset 0
    python run_pipeline.py --all
    python run_pipeline.py --from-level 3 --jurisdictions Австралия
    python run_pipeline.py --level phase2

Options:
    --jurisdictions NAMES  Space-separated list of jurisdiction names (Russian or English)
    --batch N              Number of jurisdictions to process
    --offset M             Offset into registry (default: 0)
    --all                  Process all jurisdictions from registry
    --from-level LEVEL     Start from this level (1, 2, 3, phase2, 4)
    --level LEVEL          Run only this level
    --phase2-mode MODE     Phase 2 mode: basic (pass1+pass2) or extended (pass1+3p+pass2-new)
                           Default: basic
"""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path

# Ensure project src is on the path when run as script
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

# ---------------------------------------------------------------------------
# Config and logging
# ---------------------------------------------------------------------------
from pipeline.config import (
    COUNTRIES_DIR,
    LOGS_DIR,
    LEVEL1_STATE_FILE,
    LEVEL2_STATE_FILE,
    LEVEL3_V2_STATE_FILE,
    PHASE2_STATE_FILE,
    SUPRANATIONAL_DIR,
    LLM_SMART_MODEL,
    LLM_FAST_MODEL,
)
from pipeline.logging_setup import get_logger
from pipeline.registry import load_jurisdictions, discover_all_venues

LOGS_DIR.mkdir(parents=True, exist_ok=True)
_today = datetime.date.today().strftime("%Y%m%d")
PIPELINE_LOG_FILE = LOGS_DIR / f"pipeline_{_today}.log"

logger = get_logger("run_pipeline", PIPELINE_LOG_FILE)

# Ordered level names for --from-level logic
LEVEL_ORDER = ["1", "2", "3", "phase2", "4"]


# ---------------------------------------------------------------------------
# Jurisdiction resolution
# ---------------------------------------------------------------------------

def resolve_jurisdictions(args: argparse.Namespace) -> list[dict]:
    """
    Build the list of jurisdiction dicts to process based on CLI args.

    Returns list of registry entries:
      {name_ru, name_en, market_group, eu_member, eu_note, ...}
    """
    registry = load_jurisdictions()

    if args.all:
        logger.info("Mode: --all — processing all %d jurisdictions from registry", len(registry))
        return registry

    if args.jurisdictions:
        # Filter registry by name_ru or name_en (case-insensitive match)
        names = set(n.strip() for n in args.jurisdictions)
        result = [
            j for j in registry
            if j.get("name_ru") in names or j.get("name_en") in names
        ]
        missing = names - {j.get("name_ru") for j in result} - {j.get("name_en") for j in result}
        if missing:
            logger.warning("Jurisdictions not found in registry: %s", missing)
        logger.info(
            "Mode: --jurisdictions — resolved %d jurisdictions: %s",
            len(result),
            [j["name_ru"] for j in result],
        )
        return result

    if args.batch is not None:
        offset = args.offset or 0
        batch = registry[offset: offset + args.batch]
        logger.info(
            "Mode: --batch %d --offset %d — processing %d jurisdictions",
            args.batch, offset, len(batch),
        )
        return batch

    # Fallback: no filter provided — treat as --all
    logger.warning("No jurisdiction filter specified; defaulting to --all (%d jurisdictions)", len(registry))
    return registry


# ---------------------------------------------------------------------------
# EU framework note helper
# ---------------------------------------------------------------------------

def _load_eu_note() -> str | None:
    """
    Read supranational/eu.json if it exists and return its content as a string.
    Returns None if the file does not exist.
    """
    eu_path = SUPRANATIONAL_DIR / "eu.json"
    if not eu_path.exists():
        return None
    try:
        with open(eu_path, encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, ensure_ascii=False)
    except Exception as exc:
        logger.warning("Could not load eu.json: %s", exc)
        return None


def _l1_complete_for(name_ru: str) -> bool:
    """Return True if jurisdiction_card.json already exists (L1 done)."""
    card_path = COUNTRIES_DIR / name_ru / "level_1" / "jurisdiction_card.json"
    return card_path.exists()


# ---------------------------------------------------------------------------
# Level runners
# ---------------------------------------------------------------------------

def run_level1(jurisdictions: list[dict]) -> None:
    """Run Level 1 for the given batch of jurisdictions."""
    logger.info("========== Level 1 Start ==========")

    from pipeline.parallel_runner import load_state
    from level_1.eu_framework import run_full as run_eu
    from level_1.jurisdiction_runner import (
        launch_all_1a, poll_all_1a,
        launch_all_1b, poll_all_1b,
        launch_all_1c, poll_all_1c,
    )
    from level_1.postprocess import process_all as process_all_l1

    # --- EU Framework (only if supranational/eu.json does not yet exist) ---
    eu_path = SUPRANATIONAL_DIR / "eu.json"
    if not eu_path.exists():
        logger.info("--- L1 Step 1: EU Framework ---")
        run_eu()
    else:
        logger.info("--- L1 Step 1: EU Framework already done (skipping) ---")

    state = load_state(LEVEL1_STATE_FILE)

    logger.info("--- L1 Step 2: Launch 1A ---")
    launch_all_1a(state, jurisdictions=jurisdictions)

    logger.info("--- L1 Step 3: Poll 1A ---")
    poll_all_1a(state, jurisdictions=jurisdictions)

    logger.info("--- L1 Step 4: Launch 1B ---")
    launch_all_1b(state, jurisdictions=jurisdictions)

    logger.info("--- L1 Step 5: Poll 1B ---")
    poll_all_1b(state, jurisdictions=jurisdictions)

    logger.info("--- L1 Step 6: Launch 1C ---")
    launch_all_1c(state, jurisdictions=jurisdictions)

    logger.info("--- L1 Step 7: Poll 1C ---")
    poll_all_1c(state, jurisdictions=jurisdictions)

    logger.info("--- L1 Step 8: Postprocess ---")
    process_all_l1(jurisdictions=jurisdictions)

    logger.info("--- L1 Step 9: Add citations ---")
    from pipeline.sources import process_level1_citations
    process_level1_citations(jurisdictions=[j["name_ru"] for j in jurisdictions])

    logger.info("--- L1 Step 10: Normalize L1 fields ---")
    from pipeline.l1_l2_normalize import process_l1_normalizations
    process_l1_normalizations(jurisdictions=[j["name_ru"] for j in jurisdictions])

    logger.info("--- L1 Step 11: Classify source types ---")
    from pipeline.source_classifier import process_source_types
    process_source_types(jurisdictions=[j["name_ru"] for j in jurisdictions])

    logger.info("--- L1 Step 12: Clean excerpt artifacts ---")
    from pipeline.excerpt_cleaner import run_excerpt_cleanup
    run_excerpt_cleanup(jurisdictions=[j["name_ru"] for j in jurisdictions])

    logger.info("--- L1 Step 13: Join fragmented excerpts ---")
    from pipeline.excerpt_joiner import run_excerpt_joiner
    run_excerpt_joiner(jurisdictions=[j["name_ru"] for j in jurisdictions])

    logger.info("--- L1 Step 14: Translate jurisdiction notes ---")
    from pipeline.translate_ru_fields import translate_jurisdiction_notes
    from langchain_openai import ChatOpenAI
    _llm_l1_translate = ChatOpenAI(model=LLM_FAST_MODEL, api_key=os.environ["OPENAI_API_KEY"], temperature=0)
    translate_jurisdiction_notes(llm=_llm_l1_translate, jurisdictions=[j["name_ru"] for j in jurisdictions])

    logger.info("========== Level 1 Complete ==========")


def run_level2(venues: list[dict]) -> None:
    """Run Level 2 for the given list of venue configs."""
    if not venues:
        logger.warning("Level 2: no venues to process — skipping")
        return

    logger.info("========== Level 2 Start (venues: %d) ==========", len(venues))

    from level_2.venue_runner import load_state as load_state_l2, launch_all_2a, poll_all_2a
    from level_2.prompt_generator import generate_all_prompts
    from level_2.postprocess import process_all as process_all_l2

    logger.info("--- L2 Step 1: Generate 2A prompts ---")
    generate_all_prompts(venues=venues)

    state_l2 = load_state_l2()

    logger.info("--- L2 Step 2: Launch 2A ---")
    launch_all_2a(state_l2, venues=venues)

    logger.info("--- L2 Step 3: Poll 2A ---")
    poll_all_2a(state_l2, venues=venues)

    logger.info("--- L2 Step 4: Postprocess ---")
    process_all_l2(venues=venues)

    logger.info("--- L2 Step 5: Add citations ---")
    from pipeline.sources import process_level2_citations
    process_level2_citations(venues=[v["venue_key"] for v in venues])

    logger.info("--- L2 Step 6: Normalize L2 fields ---")
    from pipeline.l1_l2_normalize import process_l2_normalizations
    jurisdiction_names = list({v.get("name_ru") for v in venues if v.get("name_ru")})
    process_l2_normalizations(jurisdictions=jurisdiction_names)

    logger.info("--- L2 Step 7: Classify source types ---")
    from pipeline.source_classifier import process_source_types
    process_source_types(jurisdictions=jurisdiction_names)

    logger.info("--- L2 Step 8: Clean excerpt artifacts ---")
    from pipeline.excerpt_cleaner import run_excerpt_cleanup
    run_excerpt_cleanup(jurisdictions=jurisdiction_names)

    logger.info("--- L2 Step 9: Join fragmented excerpts ---")
    from pipeline.excerpt_joiner import run_excerpt_joiner
    run_excerpt_joiner(jurisdictions=jurisdiction_names)

    logger.info("========== Level 2 Complete ==========")


def run_level3(venues: list[dict]) -> None:
    """Run Level 3 for the given list of venue configs."""
    if not venues:
        logger.warning("Level 3: no venues to process — skipping")
        return

    logger.info("========== Level 3 Start (venues: %d) ==========", len(venues))

    from level_3.venue_runner import (
        load_state as load_state_l3,
        build_and_save_all_prompts,
        launch_all_venues,
        poll_all_venues,
    )

    state_l3 = load_state_l3()

    logger.info("--- L3 Step 1: Build prompts ---")
    build_and_save_all_prompts(state_l3, venues=venues)

    logger.info("--- L3 Step 2: Launch Parallel tasks ---")
    launch_all_venues(state_l3, venues=venues)

    logger.info("--- L3 Step 3: Poll tasks ---")
    poll_all_venues(state_l3, venues=venues)

    logger.info("--- L3 Step 3.5: Canonical tier mapping ---")
    from pipeline.tier_mapper import run_canonical_tier_mapping
    jurisdiction_names_for_tier_map = list({v.get("name_ru") for v in venues if v.get("name_ru")})
    run_canonical_tier_mapping(jurisdictions=jurisdiction_names_for_tier_map)

    logger.info("--- L3 Step 3.6: Update cells_list from tier maps ---")
    from pipeline.tier_mapper import update_cells_list_from_tier_maps
    update_cells_list_from_tier_maps(jurisdictions=jurisdiction_names_for_tier_map)

    logger.info("--- L3 Step 4: Postprocess ---")
    try:
        from level_3.postprocess_l3 import postprocess_all_venues
        postprocess_all_venues(state_l3)
    except ImportError:
        logger.warning("postprocess_l3 not implemented — skipping")

    logger.info("--- L3 Step 5: Validate ---")
    try:
        from level_3.validator import validate_all_venues
        validate_all_venues(state_l3)
    except ImportError:
        logger.warning("validator not implemented — skipping")

    logger.info("--- L3 Step 6: Add citations ---")
    from pipeline.sources import process_level3_citations
    process_level3_citations()

    logger.info("--- L3 Step 7: Classify L3 citation types ---")
    from pipeline.source_classifier import process_l3_citation_types
    jurisdiction_names = list({v.get("name_ru") for v in venues if v.get("name_ru")})
    process_l3_citation_types(jurisdiction_names if jurisdiction_names else None)

    logger.info("--- L3 Step 8: Fix 'Fetched web page' titles ---")
    from pipeline.source_classifier import fix_fetched_web_page_titles
    fix_fetched_web_page_titles(jurisdiction_names if jurisdiction_names else None)

    logger.info("--- L3 Step 9: Clean excerpt artifacts ---")
    from pipeline.excerpt_cleaner import run_excerpt_cleanup
    run_excerpt_cleanup(jurisdictions=jurisdiction_names if jurisdiction_names else None)

    logger.info("--- L3 Step 10: Join fragmented excerpts ---")
    from pipeline.excerpt_joiner import run_excerpt_joiner
    run_excerpt_joiner(jurisdictions=jurisdiction_names if jurisdiction_names else None)

    logger.info("--- L3 Step 11: Translate section descriptions to Russian ---")
    from pipeline.l3_translate import run_l3_translate
    from langchain_openai import ChatOpenAI
    llm_translate = ChatOpenAI(
        model=LLM_FAST_MODEL,
        api_key=os.environ["OPENAI_API_KEY"],
        temperature=0,
    )
    run_l3_translate(llm=llm_translate, jurisdictions=jurisdiction_names if jurisdiction_names else None)

    logger.info("--- L3 Step 12: Build matrix ---")
    from level_3.matrix_builder import build_matrix_all
    build_matrix_all(llm=None)  # creates LLM_FAST_MODEL internally

    logger.info("========== Level 3 Complete ==========")


def run_phase2(mode: str = "basic") -> None:
    """
    Run Phase 2 on ALL data in COUNTRIES_DIR (not filtered by batch).

    mode: "basic"    → form_groups + pass1 + pass2-new + translate
          "extended" → form_groups + pass1 + 3p-classify + 3p-execute + pass2-new + translate

    Note: basic mode uses run_new_pass2 (not the legacy run_pass2) so that
    pass2.json is produced and run_pass2_translate can consume it.
    """
    logger.info("========== Phase 2 Start (mode: %s) ==========", mode)

    from level_3.phase2_runner import (
        load_state as load_state_phase2,
        form_groups,
        run_pass1,
        run_all_extended,
        run_new_pass2,
        run_pass2_translate,
        _get_llm as _get_llm_phase2,
    )

    state_phase2 = load_state_phase2()

    if mode == "extended":
        run_all_extended(state_phase2)
    else:
        # basic: form_groups → pass1 → pass2-new
        # Using run_new_pass2 (not legacy run_pass2) because:
        #   - run_new_pass2 writes pass2.json (the format run_pass2_translate reads)
        #   - legacy run_pass2 writes params.json which translate does not consume
        logger.info("--- Phase 2 Step 1: Form groups ---")
        form_groups(state_phase2)

        logger.info("--- Phase 2 Step 2: Pass 1 ---")
        run_pass1(state_phase2)

        logger.info("--- Phase 2 Step 3: Pass 2 (new) ---")
        llm_smart = _get_llm_phase2(LLM_SMART_MODEL)
        run_new_pass2(state=state_phase2, llm=llm_smart)

    # Translate pass2.json → pass2_ru.json (runs after both basic and extended modes).
    # Uses LLM_FAST_MODEL because translation is a straightforward task.
    # Idempotent: cells that already have pass2_ru.json are skipped automatically.
    logger.info("--- Phase 2 Step: Translate (pass2 → pass2_ru) ---")
    llm_translate = _get_llm_phase2(LLM_FAST_MODEL)
    run_pass2_translate(llm=llm_translate)

    logger.info("--- Phase 2 Step: Section keys ---")
    from pipeline.section_keys import process_section_keys
    process_section_keys()

    logger.info("--- Phase 2 Step: Translate tier names + param labels ---")
    from pipeline.translate_ru_fields import translate_phase2_fields
    from langchain_openai import ChatOpenAI
    _llm_p2_translate = ChatOpenAI(model=LLM_FAST_MODEL, api_key=os.environ["OPENAI_API_KEY"], temperature=0)
    translate_phase2_fields(llm=_llm_p2_translate, jurisdictions=None)

    logger.info("--- Phase 2 Step: Normalize param IDs ---")
    from pipeline.translate_ru_fields import normalize_param_ids
    normalize_param_ids()

    logger.info("========== Phase 2 Complete ==========")


def run_level4(jurisdictions: list[dict]) -> None:
    """Run Level 4 for the given batch of jurisdictions."""
    logger.info("========== Level 4 Start ==========")

    from level_4.level4_runner import run_level4_all, _get_llm as _get_llm_l4

    llm = _get_llm_l4(LLM_SMART_MODEL)
    run_level4_all(llm=llm, jurisdictions=jurisdictions)

    logger.info("--- L4 Step 2: Add citations ---")
    from pipeline.sources import process_level4_citations
    process_level4_citations(jurisdictions=[j["name_ru"] for j in jurisdictions])

    logger.info("--- L4 Step 3: Enrich record sources ---")
    from pipeline.level4_postprocess import process_level4_record_sources
    process_level4_record_sources(jurisdictions=[j["name_ru"] for j in jurisdictions])

    logger.info("--- L4 Step 4: Labels and articulated_by ---")
    from pipeline.level4_postprocess import process_level4_labels, process_level4_articulated_by
    process_level4_labels(jurisdictions=[j["name_ru"] for j in jurisdictions])
    process_level4_articulated_by(jurisdictions=[j["name_ru"] for j in jurisdictions])

    logger.info("--- L4 Step 5: Classify source types ---")
    from pipeline.source_classifier import process_source_types
    process_source_types(jurisdictions=[j["name_ru"] for j in jurisdictions])

    logger.info("--- L4 Step 6: Clean excerpt artifacts ---")
    from pipeline.excerpt_cleaner import run_excerpt_cleanup
    run_excerpt_cleanup(jurisdictions=[j["name_ru"] for j in jurisdictions])

    logger.info("--- L4 Step 7: Join fragmented excerpts ---")
    from pipeline.excerpt_joiner import run_excerpt_joiner
    run_excerpt_joiner(jurisdictions=[j["name_ru"] for j in jurisdictions])

    logger.info("--- L4 Step 8: Translate reforms + ptools fields ---")
    from pipeline.translate_ru_fields import translate_level4_fields
    from langchain_openai import ChatOpenAI
    _llm_l4_translate = ChatOpenAI(model=LLM_FAST_MODEL, api_key=os.environ["OPENAI_API_KEY"], temperature=0)
    translate_level4_fields(llm=_llm_l4_translate, jurisdictions=[j["name_ru"] for j in jurisdictions])

    logger.info("========== Level 4 Complete ==========")


# ---------------------------------------------------------------------------
# Discover venues (after L1)
# ---------------------------------------------------------------------------

def discover_venues(jurisdictions: list[dict]) -> list[dict]:
    """
    Discover venues for each jurisdiction from L1 outputs (venues_list.json).
    Logs a warning for any jurisdiction that has no venues.
    """
    venues = discover_all_venues(jurisdictions, COUNTRIES_DIR)

    # Per-jurisdiction warning
    found_jurisdictions = {v["name_ru"] for v in venues}
    for j in jurisdictions:
        if j["name_ru"] not in found_jurisdictions:
            logger.warning(
                "No venues discovered for jurisdiction '%s' — "
                "venues_list.json may be missing from level_1 output",
                j["name_ru"],
            )

    logger.info(
        "Discovered %d venue(s) across %d jurisdiction(s)",
        len(venues),
        len(jurisdictions),
    )
    return venues


# ---------------------------------------------------------------------------
# Venue review (control point B)
# ---------------------------------------------------------------------------

def _print_venue_review(jurisdictions: list, venues: list) -> None:
    """
    Print a venue review report comparing discovered venues with exchanges.json reference.
    Reads venues_list.json and jurisdiction_card.json directly per jurisdiction.
    """
    import json as _json
    from pipeline.config import DATA_DIR, get_country_level1_dir

    # Load exchanges.json reference
    exchanges_path = DATA_DIR.parent / "03_data" / "exchanges.json"
    reference = {}
    if exchanges_path.exists():
        raw = _json.loads(exchanges_path.read_text(encoding="utf-8"))
        for group in raw.values():  # DM / EM
            for juris_ru, venues_dict in group.items():
                reference[juris_ru] = list(venues_dict.keys())

    logger.info("=" * 60)
    logger.info("VENUE REVIEW — compare before proceeding to L2")
    logger.info("=" * 60)

    for j in jurisdictions:
        ru = j["name_ru"]
        l1_dir = get_country_level1_dir(ru)

        # Read discovered venues from venues_list.json
        venues_path = l1_dir / "venues_list.json"
        discovered = []
        if venues_path.exists():
            data = _json.loads(venues_path.read_text(encoding="utf-8"))
            discovered = [v.get("name_english", "?") for v in data.get("venues", [])]

        # Read excluded venues from jurisdiction_card.json
        excluded = []
        card_path = l1_dir / "jurisdiction_card.json"
        if card_path.exists():
            card = _json.loads(card_path.read_text(encoding="utf-8"))
            excluded = card.get("excluded_venues", [])

        ref = reference.get(ru, [])

        logger.info("")
        logger.info("  Jurisdiction: %s", ru)
        logger.info("  Discovered (%d venues):", len(discovered))
        for v in discovered:
            logger.info("    + %s", v)

        logger.info("  Reference exchanges.json (%d operators):", len(ref))
        for r in ref:
            logger.info("    * %s", r)

        if excluded:
            logger.info("  Excluded by postprocessor (%d):", len(excluded))
            for e in excluded:
                logger.info("    - %s  [%s]", e.get("name", "?"), e.get("reason", ""))

    logger.info("")
    logger.info("=" * 60)
    logger.info("Pipeline STOPPED after L1 (--stop-after-l1 flag).")
    logger.info("Review venues above, then continue with:")
    logger.info("  python run_pipeline.py --from-level 2 --jurisdictions <...>")
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def _should_run(level: str, from_level: str | None, only_level: str | None) -> bool:
    """Decide whether a given level should run given CLI flags."""
    if only_level is not None:
        return level == only_level
    if from_level is not None:
        return LEVEL_ORDER.index(level) >= LEVEL_ORDER.index(from_level)
    return True  # default: run all


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Top-level pipeline orchestrator: L1 → L2 → L3 → Phase 2 → L4"
    )

    # Jurisdiction selection (mutually exclusive group)
    jgroup = parser.add_mutually_exclusive_group()
    jgroup.add_argument(
        "--jurisdictions",
        nargs="+",
        metavar="NAME",
        help="Space-separated jurisdiction names (Russian or English)",
    )
    jgroup.add_argument(
        "--batch",
        type=int,
        metavar="N",
        help="Number of jurisdictions to process (from registry)",
    )
    jgroup.add_argument(
        "--all",
        action="store_true",
        default=False,
        help="Process all jurisdictions from registry",
    )

    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        metavar="M",
        help="Offset into registry when using --batch (default: 0)",
    )

    # Level control (mutually exclusive)
    level_group = parser.add_mutually_exclusive_group()
    level_group.add_argument(
        "--from-level",
        dest="from_level",
        choices=LEVEL_ORDER,
        metavar="{1,2,3,phase2,4}",
        help="Start pipeline from this level and run to completion",
    )
    level_group.add_argument(
        "--level",
        dest="only_level",
        choices=LEVEL_ORDER,
        metavar="{1,2,3,phase2,4}",
        help="Run only this single level",
    )

    parser.add_argument(
        "--phase2-mode",
        dest="phase2_mode",
        choices=["basic", "extended"],
        default="basic",
        help="Phase 2 mode: basic (pass1+pass2) or extended (pass1+3p+pass2-new) [default: basic]",
    )

    parser.add_argument(
        "--stop-after-l1",
        action="store_true",
        help="Stop after Level 1 venue discovery and print venue review report. "
             "Use --from-level 2 to continue after review.",
    )

    args = parser.parse_args()

    # ---- Resolve jurisdiction list ----
    jurisdictions = resolve_jurisdictions(args)
    if not jurisdictions:
        logger.error("No jurisdictions resolved — nothing to do. Exiting.")
        sys.exit(1)

    # ---- Level 1 ----
    if _should_run("1", args.from_level, args.only_level):
        run_level1(jurisdictions)

    # ---- Discover venues (shared between L2, L3) ----
    # Always discover from disk so we pick up whatever L1 produced.
    # If L1 was skipped we still attempt discovery (data may already exist).
    venues = discover_venues(jurisdictions)

    if args.stop_after_l1:
        _print_venue_review(jurisdictions, venues)
        return

    # ---- Level 2 ----
    if _should_run("2", args.from_level, args.only_level):
        run_level2(venues)

    # ---- Level 3 ----
    if _should_run("3", args.from_level, args.only_level):
        run_level3(venues)

    # ---- Phase 2 ----
    if _should_run("phase2", args.from_level, args.only_level):
        run_phase2(mode=args.phase2_mode)

    # ---- Level 4 ----
    if _should_run("4", args.from_level, args.only_level):
        run_level4(jurisdictions)

    logger.info("===== Pipeline run complete =====")


if __name__ == "__main__":
    main()
