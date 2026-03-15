"""
Add citations/sources from Parallel API basis to processed pipeline files.

Reads parallel_output.basis from raw Parallel output files and adds source URLs
to processed files without any LLM involvement.

Idempotent: overwrites existing sources/citations fields.

Usage:
    cd D:\\_workspace\\deep-research-listing
    venv\\Scripts\\python.exe tools/add_citations.py [--level L1|L2|L3|L4|ALL] [--dry-run]
"""

import argparse
import io
import json
import sys
from pathlib import Path

# Force UTF-8 output on Windows (avoids cp1251 UnicodeEncodeError for Cyrillic paths)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Bootstrap: add repo root to sys.path so we can import pipeline.config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "02_src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline.config import (
    PILOT_JURISDICTIONS,
    PILOT_VENUES,
    get_country_level1_dir,
    get_country_level2_dir,
    get_country_level3_dir,
    get_country_level4_dir,
)

# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------


def load_json(path: Path) -> dict | None:
    """Load JSON from path; return None if file missing or parse error."""
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"  [WARN] Could not read {path}: {exc}")
        return None


def save_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Core citation extraction
# ---------------------------------------------------------------------------


def extract_sources_from_raw(raw_file_path: Path) -> list[dict]:
    """
    Extract unique citation sources from a raw file's parallel_output.basis.
    Returns list of {"url": ..., "title": ..., "field": ...} dicts.
    """
    data = load_json(raw_file_path)
    if not data:
        return []
    parallel_output = data.get("parallel_output", {})
    if not parallel_output:
        return []
    basis = parallel_output.get("basis") or []

    seen_urls: set[str] = set()
    sources: list[dict] = []
    for field_basis in basis:
        field = field_basis.get("field", "")
        for citation in (field_basis.get("citations") or []):
            url = citation.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                sources.append({
                    "url": url,
                    "title": citation.get("title") or "",
                    "field": field,
                })
    return sources


def merge_sources_dedup(lists: list[list[dict]]) -> list[dict]:
    """Merge multiple source lists, deduplicating by URL (first-seen wins)."""
    seen_urls: set[str] = set()
    merged: list[dict] = []
    for source_list in lists:
        for s in source_list:
            url = s.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                merged.append(s)
    return merged


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
# Level 1: jurisdiction_card.json
# ---------------------------------------------------------------------------


def process_level1(dry_run: bool, stats: Stats) -> None:
    print("\n=== Level 1: jurisdiction_card.json ===")
    raw_names = ["1A_architecture.json", "1B_institutional.json", "1C_venues.json"]

    for jur in PILOT_JURISDICTIONS:
        name_ru = jur["name_ru"]
        l1_dir = get_country_level1_dir(name_ru)
        processed_path = l1_dir / "jurisdiction_card.json"

        # Gather sources from all three raw files
        all_sources: list[list[dict]] = []
        has_any_parallel_output = False
        for raw_name in raw_names:
            raw_path = l1_dir / raw_name
            if not raw_path.exists():
                print(f"  [WARN] Raw file not found, skipping contribution: {raw_path}")
                stats.skipped_no_raw += 1
                continue
            raw_data = load_json(raw_path)
            if not raw_data or "parallel_output" not in raw_data:
                print(f"  [WARN] No parallel_output in: {raw_path}")
                stats.skipped_no_parallel_output += 1
                continue
            has_any_parallel_output = True
            sources = extract_sources_from_raw(raw_path)
            all_sources.append(sources)

        if not has_any_parallel_output:
            print(f"  [{name_ru}] No parallel_output found in any raw file — skipping.")
            continue

        merged = merge_sources_dedup(all_sources)

        if not processed_path.exists():
            print(f"  [{name_ru}] Processed file not found — skipping: {processed_path}")
            stats.skipped_no_processed += 1
            continue

        print(
            f"  [{name_ru}] {len(merged)} sources → {processed_path.name}"
            + (" [DRY-RUN]" if dry_run else "")
        )

        if not dry_run:
            try:
                processed = load_json(processed_path)
                if processed is None:
                    print(f"  [ERROR] Could not load processed file: {processed_path}")
                    stats.errors += 1
                    continue
                processed["sources"] = merged
                save_json(processed_path, processed)
                stats.updated += 1
            except Exception as exc:
                print(f"  [ERROR] Failed to write {processed_path}: {exc}")
                stats.errors += 1
        else:
            stats.updated += 1


# ---------------------------------------------------------------------------
# Level 2: venue_card.json
# ---------------------------------------------------------------------------


def process_level2(dry_run: bool, stats: Stats) -> None:
    print("\n=== Level 2: venue_card.json ===")

    for venue in PILOT_VENUES:
        name_ru = venue["name_ru"]
        venue_key = venue["venue_key"]
        l2_dir = get_country_level2_dir(name_ru, venue_key)
        raw_path = l2_dir / "2A_structure.json"
        processed_path = l2_dir / "venue_card.json"

        if not raw_path.exists():
            print(f"  [WARN] Raw file not found: {raw_path}")
            stats.skipped_no_raw += 1
            continue

        raw_data = load_json(raw_path)
        if not raw_data or "parallel_output" not in raw_data:
            print(f"  [WARN] No parallel_output in: {raw_path}")
            stats.skipped_no_parallel_output += 1
            continue

        sources = extract_sources_from_raw(raw_path)

        if not processed_path.exists():
            print(f"  [{venue_key}] Processed file not found — skipping: {processed_path}")
            stats.skipped_no_processed += 1
            continue

        print(
            f"  [{venue_key}] {len(sources)} sources → {processed_path.name}"
            + (" [DRY-RUN]" if dry_run else "")
        )

        if not dry_run:
            try:
                processed = load_json(processed_path)
                if processed is None:
                    print(f"  [ERROR] Could not load processed file: {processed_path}")
                    stats.errors += 1
                    continue
                processed["sources"] = sources
                save_json(processed_path, processed)
                stats.updated += 1
            except Exception as exc:
                print(f"  [ERROR] Failed to write {processed_path}: {exc}")
                stats.errors += 1
        else:
            stats.updated += 1


# ---------------------------------------------------------------------------
# Level 3: per-cell raw files (3A_raw.json, 3B_raw.json, 3C_raw.json)
# ---------------------------------------------------------------------------


def _add_citations_to_raw_file(raw_path: Path, label: str, dry_run: bool, stats: Stats) -> None:
    """Add citations field to a single raw file that has parallel_output.basis."""
    raw_data = load_json(raw_path)
    if not raw_data or "parallel_output" not in raw_data:
        stats.skipped_no_parallel_output += 1
        return

    citations = extract_sources_from_raw(raw_path)
    print(
        f"    [{label}] {len(citations)} citations"
        + (" [DRY-RUN]" if dry_run else "")
    )

    if not dry_run:
        try:
            raw_data["citations"] = citations
            save_json(raw_path, raw_data)
            stats.updated += 1
        except Exception as exc:
            print(f"    [ERROR] Failed to write {raw_path}: {exc}")
            stats.errors += 1
    else:
        stats.updated += 1


def process_level3(dry_run: bool, stats: Stats) -> None:
    """
    Add citations to L3 raw files from two sources:
    - Phase 1: per-cell directories (direct Parallel output, have parallel_output)
    - Phase 2: _parallel_raw/ subdirectory (instrument-class level Parallel output)
    """
    print("\n=== Level 3: raw files ===")
    query_types = ["3A", "3B", "3C"]

    for venue in PILOT_VENUES:
        name_ru = venue["name_ru"]
        venue_key = venue["venue_key"]
        l3_dir = get_country_level3_dir(name_ru, venue_key)

        if not l3_dir.exists():
            print(f"  [WARN] L3 dir not found: {l3_dir}")
            continue

        print(f"  [{venue_key}]")

        # Phase 2: _parallel_raw/*.json files
        parallel_raw_dir = l3_dir / "_parallel_raw"
        if parallel_raw_dir.exists():
            raw_files = sorted(parallel_raw_dir.glob("*_raw.json"))
            if raw_files:
                print(f"    Phase 2 (_parallel_raw): {len(raw_files)} files")
                for raw_path in raw_files:
                    _add_citations_to_raw_file(raw_path, raw_path.stem, dry_run, stats)

        # Phase 1: per-cell subdirectories (non-underscore-prefixed)
        cell_dirs = sorted(
            p for p in l3_dir.iterdir()
            if p.is_dir() and not p.name.startswith("_")
        )
        if cell_dirs:
            print(f"    Phase 1 (per-cell): {len(cell_dirs)} cells")
            for cell_dir in cell_dirs:
                cell_id = cell_dir.name
                for query_type in query_types:
                    raw_path = cell_dir / f"{query_type}_raw.json"
                    if not raw_path.exists():
                        continue
                    _add_citations_to_raw_file(raw_path, f"{cell_id}/{query_type}", dry_run, stats)


# ---------------------------------------------------------------------------
# Level 4: level4.json
# ---------------------------------------------------------------------------


def process_level4(dry_run: bool, stats: Stats) -> None:
    print("\n=== Level 4: level4.json ===")

    for jur in PILOT_JURISDICTIONS:
        name_ru = jur["name_ru"]
        l4_dir = get_country_level4_dir(name_ru)
        raw_path = l4_dir / "4A_raw.json"
        processed_path = l4_dir / "level4.json"

        if not raw_path.exists():
            print(f"  [WARN] Raw file not found: {raw_path}")
            stats.skipped_no_raw += 1
            continue

        raw_data = load_json(raw_path)
        if not raw_data or "parallel_output" not in raw_data:
            print(f"  [WARN] No parallel_output in: {raw_path}")
            stats.skipped_no_parallel_output += 1
            continue

        sources = extract_sources_from_raw(raw_path)

        if not processed_path.exists():
            print(f"  [{name_ru}] Processed file not found — skipping: {processed_path}")
            stats.skipped_no_processed += 1
            continue

        print(
            f"  [{name_ru}] {len(sources)} sources → {processed_path.name}"
            + (" [DRY-RUN]" if dry_run else "")
        )

        if not dry_run:
            try:
                processed = load_json(processed_path)
                if processed is None:
                    print(f"  [ERROR] Could not load processed file: {processed_path}")
                    stats.errors += 1
                    continue
                processed["sources"] = sources
                save_json(processed_path, processed)
                stats.updated += 1
            except Exception as exc:
                print(f"  [ERROR] Failed to write {processed_path}: {exc}")
                stats.errors += 1
        else:
            stats.updated += 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


LEVEL_HANDLERS = {
    "L1": process_level1,
    "L2": process_level2,
    "L3": process_level3,
    "L4": process_level4,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Add citations/sources from Parallel API basis to processed pipeline files."
        )
    )
    parser.add_argument(
        "--level",
        default="ALL",
        choices=["L1", "L2", "L3", "L4", "ALL"],
        help="Which pipeline level to process (default: ALL).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing any files.",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("=== DRY-RUN MODE — no files will be written ===")

    levels = list(LEVEL_HANDLERS.keys()) if args.level == "ALL" else [args.level]

    stats = Stats()
    for level in levels:
        LEVEL_HANDLERS[level](args.dry_run, stats)

    print(f"\n=== Done ===\n{stats.summary()}")


if __name__ == "__main__":
    main()
