"""
Sources extraction and citation management for the pipeline.

Reads parallel_output.basis from raw Parallel output files, extracts
source URLs with excerpts, and writes them to processed pipeline files.

Idempotent: overwrites existing sources/citations fields.
"""
import json
import os
import tempfile
import datetime
from pathlib import Path

from pipeline.config import COUNTRIES_DIR, LOGS_DIR
from pipeline.logging_setup import get_logger

_today = datetime.date.today().strftime("%Y%m%d")
_SOURCES_LOG_FILE = LOGS_DIR / f"sources_{_today}.log"

logger = get_logger("sources", _SOURCES_LOG_FILE)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict | None:
    """Load JSON from path; return None if file missing or parse error."""
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return None


def _save_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _save_json_atomic(path: Path, data: dict) -> None:
    """Write JSON atomically using a temp file + os.replace to avoid partial writes."""
    dir_ = path.parent
    fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Statistics counter
# ---------------------------------------------------------------------------


class Stats:
    def __init__(self) -> None:
        self.updated = 0
        self.skipped_no_raw = 0
        self.skipped_no_parallel_output = 0
        self.skipped_no_processed = 0
        self.errors = 0

    def summary(self) -> str:
        return (
            f"Updated: {self.updated} | "
            f"Skipped (no raw): {self.skipped_no_raw} | "
            f"Skipped (no parallel_output): {self.skipped_no_parallel_output} | "
            f"Skipped (no processed): {self.skipped_no_processed} | "
            f"Errors: {self.errors}"
        )


# ---------------------------------------------------------------------------
# Core citation extraction
# ---------------------------------------------------------------------------


def extract_sources_from_raw(raw_file_path: Path) -> list[dict]:
    """
    Extract citation sources from a raw file's parallel_output.basis.

    Returns one entry per (basis_field, citation) pair — NO deduplication.
    Each entry: {"url", "title", "field", "excerpts", "confidence"}
    """
    data = _load_json(raw_file_path)
    if not data:
        return []
    parallel_output = data.get("parallel_output", {})
    if not parallel_output:
        return []
    basis = parallel_output.get("basis") or []

    result = []
    for field_basis in basis:
        field = field_basis.get("field", "")
        basis_confidence = field_basis.get("confidence", "")
        for citation in (field_basis.get("citations") or []):
            url = citation.get("url", "")
            if not url:
                continue
            result.append({
                "url": url,
                "title": citation.get("title") or "",
                "field": field,
                "excerpts": list(citation.get("excerpts") or []),
                "confidence": citation.get("confidence") or basis_confidence or "",
            })
    return result


def merge_sources(lists: list[list[dict]]) -> list[dict]:
    """Merge multiple source lists. No deduplication — preserves all entries."""
    result = []
    for source_list in lists:
        result.extend(source_list)
    return result


# ---------------------------------------------------------------------------
# Level 1: jurisdiction_card.json
# ---------------------------------------------------------------------------


def process_level1_citations(
    jurisdictions: list[str] | None = None,
    dry_run: bool = False,
    stats: Stats | None = None,
) -> Stats:
    """
    Add/update sources in jurisdiction_card.json for all (or specified) jurisdictions.

    jurisdictions: list of name_ru strings; if None → process all on disk.
    dry_run: if True, no files are written.
    stats: Stats instance to accumulate counts; creates a new one if None.
    """
    if stats is None:
        stats = Stats()

    logger.info("=== Level 1 citations: jurisdiction_card.json ===")
    raw_names = ["1A_architecture.json", "1B_institutional.json", "1C_venues.json"]

    for country_dir in sorted(COUNTRIES_DIR.iterdir()):
        if not country_dir.is_dir():
            continue
        name = country_dir.name

        # Filter by requested jurisdictions if specified
        if jurisdictions is not None and name not in jurisdictions:
            continue

        l1_dir = country_dir / "level_1"
        processed_path = l1_dir / "jurisdiction_card.json"

        if not processed_path.exists():
            stats.skipped_no_processed += 1
            continue

        # Gather sources from all three raw files
        all_sources: list[list[dict]] = []
        has_any_parallel_output = False
        for raw_name in raw_names:
            raw_path = l1_dir / raw_name
            if not raw_path.exists():
                continue
            raw_data = _load_json(raw_path)
            if not raw_data or "parallel_output" not in raw_data:
                continue
            has_any_parallel_output = True
            all_sources.append(extract_sources_from_raw(raw_path))

        if not has_any_parallel_output:
            logger.info("[%s] No parallel_output in any raw file — skipping.", name)
            stats.skipped_no_parallel_output += 1
            continue

        merged = merge_sources(all_sources)
        logger.info(
            "[%s] %d sources → jurisdiction_card.json%s",
            name,
            len(merged),
            " [DRY-RUN]" if dry_run else "",
        )

        if not dry_run:
            try:
                processed = _load_json(processed_path)
                if processed is None:
                    logger.error("Could not load %s", processed_path)
                    stats.errors += 1
                    continue
                processed["sources"] = merged
                _save_json(processed_path, processed)
                stats.updated += 1
            except Exception as exc:
                logger.error("Failed to write %s: %s", processed_path, exc)
                stats.errors += 1
        else:
            stats.updated += 1

    logger.info("Level 1 citations done. %s", stats.summary())
    return stats


# ---------------------------------------------------------------------------
# Level 2: venue_card.json
# ---------------------------------------------------------------------------


def process_level2_citations(
    venues: list[str] | None = None,
    dry_run: bool = False,
    stats: Stats | None = None,
) -> Stats:
    """
    Add/update sources in venue_card.json for all (or specified) venues.

    venues: list of venue_key strings; if None → process all on disk.
    dry_run: if True, no files are written.
    stats: Stats instance to accumulate counts; creates a new one if None.
    """
    if stats is None:
        stats = Stats()

    logger.info("=== Level 2 citations: venue_card.json ===")

    for country_dir in sorted(COUNTRIES_DIR.iterdir()):
        if not country_dir.is_dir():
            continue
        l2_root = country_dir / "level_2"
        if not l2_root.exists():
            continue
        for venue_dir in sorted(l2_root.iterdir()):
            if not venue_dir.is_dir():
                continue
            venue_key = venue_dir.name

            # Filter by requested venues if specified
            if venues is not None and venue_key not in venues:
                continue

            raw_path = venue_dir / "2A_structure.json"
            processed_path = venue_dir / "venue_card.json"

            if not processed_path.exists():
                stats.skipped_no_processed += 1
                continue

            if not raw_path.exists():
                stats.skipped_no_raw += 1
                continue

            raw_data = _load_json(raw_path)
            if not raw_data or "parallel_output" not in raw_data:
                stats.skipped_no_parallel_output += 1
                continue

            sources = extract_sources_from_raw(raw_path)
            logger.info(
                "[%s] %d sources → venue_card.json%s",
                venue_key,
                len(sources),
                " [DRY-RUN]" if dry_run else "",
            )

            if not dry_run:
                try:
                    processed = _load_json(processed_path)
                    if processed is None:
                        logger.error("Could not load %s", processed_path)
                        stats.errors += 1
                        continue
                    processed["sources"] = sources
                    _save_json(processed_path, processed)
                    stats.updated += 1
                except Exception as exc:
                    logger.error("Failed to write %s: %s", processed_path, exc)
                    stats.errors += 1
            else:
                stats.updated += 1

    logger.info("Level 2 citations done. %s", stats.summary())
    return stats


# ---------------------------------------------------------------------------
# Level 3: per-cell raw files (3A_raw.json, 3B_raw.json, 3C_raw.json)
# ---------------------------------------------------------------------------


def _enrich_content_with_reasoning(raw_data: dict) -> bool:
    """
    Copy reasoning from parallel_output.basis[] into content sections.
    Adds 'reasoning' field to each content section that has a matching basis entry.
    Returns True if any changes were made.
    """
    parallel_output = raw_data.get("parallel_output", {})
    basis = parallel_output.get("basis") or []
    content = raw_data.get("content", {})
    if not basis or not content:
        return False

    changed = False
    for field_basis in basis:
        field = field_basis.get("field", "")
        reasoning = field_basis.get("reasoning", "")
        if not field or not reasoning:
            continue

        # Direct match (FLAT sections)
        section = content.get(field)
        if isinstance(section, dict) and "reasoning" not in section:
            section["reasoning"] = reasoning
            changed = True

    return changed


def _add_citations_to_raw_file(
    raw_path: Path, label: str, dry_run: bool, stats: Stats
) -> None:
    """Add citations field to a single raw file that has parallel_output.basis."""
    raw_data = _load_json(raw_path)
    if not raw_data or "parallel_output" not in raw_data:
        stats.skipped_no_parallel_output += 1
        return

    citations = extract_sources_from_raw(raw_path)

    # Enrich content sections with reasoning from basis
    reasoning_added = _enrich_content_with_reasoning(raw_data)
    if reasoning_added:
        logger.info("[%s] reasoning enriched from basis", label)

    logger.info(
        "[%s] %d citations%s",
        label,
        len(citations),
        " [DRY-RUN]" if dry_run else "",
    )

    if not dry_run:
        try:
            raw_data["citations"] = citations
            _save_json(raw_path, raw_data)
            stats.updated += 1
        except Exception as exc:
            logger.error("Failed to write %s: %s", raw_path, exc)
            stats.errors += 1
    else:
        stats.updated += 1


def process_level3_citations(
    dry_run: bool = False,
    stats: Stats | None = None,
) -> Stats:
    """
    Add citations to L3 raw files from two sources:
    - Phase 1: per-cell directories (direct Parallel output, have parallel_output)
    - Phase 2: _parallel_raw/ subdirectory (instrument-class level Parallel output)

    dry_run: if True, no files are written.
    stats: Stats instance to accumulate counts; creates a new one if None.
    """
    if stats is None:
        stats = Stats()

    logger.info("=== Level 3 citations: raw files ===")
    query_types = ["3A", "3B", "3C"]

    for country_dir in sorted(COUNTRIES_DIR.iterdir()):
        if not country_dir.is_dir():
            continue
        l3_root = country_dir / "level_3"
        if not l3_root.exists():
            continue
        for venue_dir in sorted(l3_root.iterdir()):
            if not venue_dir.is_dir():
                continue
            venue_key = venue_dir.name
            l3_dir = venue_dir

            logger.info("[%s]", venue_key)

            # Phase 2: _parallel_raw/*.json files
            parallel_raw_dir = l3_dir / "_parallel_raw"
            if parallel_raw_dir.exists():
                raw_files = sorted(parallel_raw_dir.glob("*_raw.json"))
                if raw_files:
                    logger.info(
                        "  Phase 2 (_parallel_raw): %d files", len(raw_files)
                    )
                    for raw_path in raw_files:
                        _add_citations_to_raw_file(
                            raw_path, raw_path.stem, dry_run, stats
                        )

            # Phase 1: per-cell subdirectories (non-underscore-prefixed)
            cell_dirs = sorted(
                p for p in l3_dir.iterdir()
                if p.is_dir() and not p.name.startswith("_")
            )
            if cell_dirs:
                logger.info("  Phase 1 (per-cell): %d cells", len(cell_dirs))
                for cell_dir in cell_dirs:
                    cell_id = cell_dir.name
                    for query_type in query_types:
                        raw_path = cell_dir / f"{query_type}_raw.json"
                        if not raw_path.exists():
                            continue
                        _add_citations_to_raw_file(
                            raw_path,
                            f"{cell_id}/{query_type}",
                            dry_run,
                            stats,
                        )

    logger.info("Level 3 citations done. %s", stats.summary())
    return stats


# ---------------------------------------------------------------------------
# Level 4: level4.json
# ---------------------------------------------------------------------------


def process_level4_citations(
    jurisdictions: list[str] | None = None,
    dry_run: bool = False,
    stats: Stats | None = None,
) -> Stats:
    """
    Add/update sources in level4.json for all (or specified) jurisdictions.

    jurisdictions: list of name_ru strings; if None → process all on disk.
    dry_run: if True, no files are written.
    stats: Stats instance to accumulate counts; creates a new one if None.
    """
    if stats is None:
        stats = Stats()

    logger.info("=== Level 4 citations: level4.json ===")

    for country_dir in sorted(COUNTRIES_DIR.iterdir()):
        if not country_dir.is_dir():
            continue
        name = country_dir.name

        # Filter by requested jurisdictions if specified
        if jurisdictions is not None and name not in jurisdictions:
            continue

        l4_dir = country_dir / "level_4"
        if not l4_dir.exists():
            continue
        raw_path = l4_dir / "4A_raw.json"
        processed_path = l4_dir / "level4.json"

        if not processed_path.exists():
            stats.skipped_no_processed += 1
            continue

        if not raw_path.exists():
            stats.skipped_no_raw += 1
            continue

        raw_data = _load_json(raw_path)
        if not raw_data or "parallel_output" not in raw_data:
            stats.skipped_no_parallel_output += 1
            continue

        sources = extract_sources_from_raw(raw_path)
        logger.info(
            "[%s] %d sources → level4.json%s",
            name,
            len(sources),
            " [DRY-RUN]" if dry_run else "",
        )

        if not dry_run:
            try:
                processed = _load_json(processed_path)
                if processed is None:
                    logger.error("Could not load %s", processed_path)
                    stats.errors += 1
                    continue
                processed["sources"] = sources
                _save_json(processed_path, processed)
                stats.updated += 1
            except Exception as exc:
                logger.error("Failed to write %s: %s", processed_path, exc)
                stats.errors += 1
        else:
            stats.updated += 1

    logger.info("Level 4 citations done. %s", stats.summary())
    return stats


