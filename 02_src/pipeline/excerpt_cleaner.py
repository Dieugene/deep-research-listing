"""
Task 024: Clean Google snippet artifacts from excerpt text.

Removes:
- Leading date prefixes: "Mon DD, YYYY - "
- Trailing "...Read more" / "...Read more"
- Mid-text snippet joins: "...Read more" followed by optional date prefix

Purely algorithmic - no LLM calls.
"""
import datetime
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

from pipeline.config import COUNTRIES_DIR, LOGS_DIR
from pipeline.logging_setup import get_logger

logger = get_logger(
    "excerpt_cleaner",
    LOGS_DIR / f"excerpt_cleaner_{datetime.date.today()}.log",
)

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"

# Date prefix: "Mon DD, YYYY — " (em-dash, en-dash, or hyphen)
_DATE_PREFIX = re.compile(
    rf"^{_MONTHS}\s+\d{{1,2}},?\s+\d{{4}}\s*[\u2014\u2013\-]\s*"
)

# Mid-text "...Read more" followed by optional whitespace and optional date prefix
# Captures the boundary between two snippets
_MID_READ_MORE = re.compile(
    rf"(?:\.{{3}}|\u2026)\s*Read\s+more\s*"
    rf"(?:{_MONTHS}\s+\d{{1,2}},?\s+\d{{4}}\s*[\u2014\u2013\-]\s*)?"
)

# Trailing "...Read more" or "...Read more" at end of string
_TRAILING_READ_MORE = re.compile(
    r"(?:\.{3}|\u2026)\s*Read\s+more\s*$"
)


def clean_excerpt(text: str) -> str:
    """Apply all cleanup rules to a single excerpt string.

    Loops until stable to handle cascading patterns (e.g. mid-text removal
    exposing a new leading date prefix).
    """
    if not text:
        return text

    result = text
    for _ in range(5):  # safety limit; typically converges in 1-2 passes
        prev = result

        # Rule 1: Mid-text "...Read more" (+ optional date) -> " ... "
        result = _MID_READ_MORE.sub(" ... ", result)

        # Rule 2: Trailing "...Read more" at end of string -> remove
        result = _TRAILING_READ_MORE.sub("", result)

        # Rule 3: Leading date prefix
        result = _DATE_PREFIX.sub("", result)

        # Rule 4: Strip whitespace
        result = result.strip()

        if result == prev:
            break

    return result


# ---------------------------------------------------------------------------
# JSON helpers (same pattern as source_classifier.py)
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | list | None:
    """Load JSON from path, returning None on error."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("File not found: %s", path)
        return None
    except json.JSONDecodeError as exc:
        logger.error("JSON decode error in %s: %s", path, exc)
        return None


def _save_json(path: Path, data) -> None:
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


# ---------------------------------------------------------------------------
# Recursive excerpt walker
# ---------------------------------------------------------------------------

def _walk_and_clean_excerpts(obj, stats: dict) -> bool:
    """
    Recursively walk a JSON structure. Find all lists named "excerpts"
    containing strings, clean each string. Mutates obj in place.
    Returns True if any excerpt was modified.
    """
    changed = False

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "excerpts" and isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        cleaned = clean_excerpt(item)
                        if cleaned != item:
                            obj[key][i] = cleaned
                            stats["cleaned"] += 1
                            changed = True
                        stats["total"] += 1
            else:
                if _walk_and_clean_excerpts(value, stats):
                    changed = True
    elif isinstance(obj, list):
        for item in obj:
            if _walk_and_clean_excerpts(item, stats):
                changed = True

    return changed


def clean_excerpts_in_file(file_path: Path) -> int:
    """
    Load JSON, find all excerpts[] arrays, clean each excerpt,
    save atomically if changed.
    Returns number of excerpts cleaned.
    """
    data = _load_json(file_path)
    if data is None:
        return 0

    stats = {"cleaned": 0, "total": 0}
    changed = _walk_and_clean_excerpts(data, stats)

    if changed:
        _save_json(file_path, data)

    return stats["cleaned"]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

# Files to scan per level
_L1_FILES = [
    "jurisdiction_card.json",
    "1A_architecture.json",
    "1B_institutional.json",
    "1C_venues.json",
]

_L2_FILES = ["venue_card.json"]

_L3_RAW_PATTERNS = ["3A_raw.json", "3B_raw.json", "3C_raw.json"]

_L4_FILES = ["level4.json", "4A_raw.json"]


def run_excerpt_cleanup(jurisdictions: Optional[list[str]] = None) -> None:
    """
    Main entry point. Scan all relevant JSON files across all levels,
    clean excerpt artifacts.

    jurisdictions: list of name_ru directory names; None = all.
    """
    logger.info("=== Excerpt cleanup: start (jurisdictions=%s) ===", jurisdictions)

    total_files_scanned = 0
    total_files_updated = 0
    total_excerpts_cleaned = 0

    # Discover jurisdiction directories
    if jurisdictions is None:
        juris_dirs = sorted(
            d for d in COUNTRIES_DIR.iterdir() if d.is_dir()
        )
    else:
        juris_dirs = [
            COUNTRIES_DIR / name for name in jurisdictions
            if (COUNTRIES_DIR / name).is_dir()
        ]

    for juris_dir in juris_dirs:
        name_ru = juris_dir.name

        # --- L1 ---
        l1_dir = juris_dir / "level_1"
        if l1_dir.exists():
            for fname in _L1_FILES:
                fpath = l1_dir / fname
                if fpath.exists():
                    total_files_scanned += 1
                    cleaned = clean_excerpts_in_file(fpath)
                    if cleaned > 0:
                        total_files_updated += 1
                        total_excerpts_cleaned += cleaned
                        logger.info("[UPDATED] %s/level_1/%s -- %d excerpts cleaned", name_ru, fname, cleaned)

        # --- L2 ---
        l2_dir = juris_dir / "level_2"
        if l2_dir.exists():
            for venue_dir in sorted(l2_dir.iterdir()):
                if not venue_dir.is_dir():
                    continue
                for fname in _L2_FILES:
                    fpath = venue_dir / fname
                    if fpath.exists():
                        total_files_scanned += 1
                        cleaned = clean_excerpts_in_file(fpath)
                        if cleaned > 0:
                            total_files_updated += 1
                            total_excerpts_cleaned += cleaned
                            logger.info("[UPDATED] %s/level_2/%s/%s -- %d excerpts cleaned",
                                        name_ru, venue_dir.name, fname, cleaned)

        # --- L3 ---
        l3_dir = juris_dir / "level_3"
        if l3_dir.exists():
            for venue_dir in sorted(l3_dir.iterdir()):
                if not venue_dir.is_dir():
                    continue

                # Phase 2: _parallel_raw/
                parallel_raw_dir = venue_dir / "_parallel_raw"
                if parallel_raw_dir.exists():
                    for raw_path in sorted(parallel_raw_dir.glob("*_raw.json")):
                        total_files_scanned += 1
                        cleaned = clean_excerpts_in_file(raw_path)
                        if cleaned > 0:
                            total_files_updated += 1
                            total_excerpts_cleaned += cleaned
                            logger.info("[UPDATED] %s/level_3/%s/_parallel_raw/%s -- %d excerpts cleaned",
                                        name_ru, venue_dir.name, raw_path.name, cleaned)

                # Phase 1: per-cell subdirectories
                for cell_dir in sorted(venue_dir.iterdir()):
                    if not cell_dir.is_dir() or cell_dir.name.startswith("_"):
                        continue
                    for fname in _L3_RAW_PATTERNS:
                        fpath = cell_dir / fname
                        if fpath.exists():
                            total_files_scanned += 1
                            cleaned = clean_excerpts_in_file(fpath)
                            if cleaned > 0:
                                total_files_updated += 1
                                total_excerpts_cleaned += cleaned
                                logger.info("[UPDATED] %s/level_3/%s/%s/%s -- %d excerpts cleaned",
                                            name_ru, venue_dir.name, cell_dir.name, fname, cleaned)

        # --- L4 ---
        l4_dir = juris_dir / "level_4"
        if l4_dir.exists():
            for fname in _L4_FILES:
                fpath = l4_dir / fname
                if fpath.exists():
                    total_files_scanned += 1
                    cleaned = clean_excerpts_in_file(fpath)
                    if cleaned > 0:
                        total_files_updated += 1
                        total_excerpts_cleaned += cleaned
                        logger.info("[UPDATED] %s/level_4/%s -- %d excerpts cleaned", name_ru, fname, cleaned)

    logger.info(
        "=== Excerpt cleanup: done -- %d files scanned, %d updated, %d excerpts cleaned ===",
        total_files_scanned, total_files_updated, total_excerpts_cleaned,
    )
