"""
Catch-up script: run citations extraction for all existing files across all levels.

Scans COUNTRIES_DIR for all files produced by Levels 1–4 and adds/updates
the sources/citations fields with excerpts from Parallel API basis.

Idempotent: safe to re-run; existing sources fields are overwritten.

Usage:
    cd D:\\_workspace\\deep-research-listing
    venv\\Scripts\\python.exe 02_src/tools/run_citations_catchup.py [--dry-run]
    venv\\Scripts\\python.exe 02_src/tools/run_citations_catchup.py --level L1
    venv\\Scripts\\python.exe 02_src/tools/run_citations_catchup.py --level L2
    venv\\Scripts\\python.exe 02_src/tools/run_citations_catchup.py --level L3
    venv\\Scripts\\python.exe 02_src/tools/run_citations_catchup.py --level L4
"""

import argparse
import io
import sys
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Bootstrap: add repo src to sys.path
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "02_src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline.sources import (  # noqa: E402
    Stats,
    process_level1_citations,
    process_level2_citations,
    process_level3_citations,
    process_level4_citations,
)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Catch-up: add/update citations (with excerpts) to all existing "
            "pipeline output files across all levels."
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

    print(
        f"=== Citations catch-up: level={args.level}"
        + (" [DRY-RUN]" if args.dry_run else "")
        + " ==="
    )

    stats = Stats()
    dry_run = args.dry_run
    level = args.level

    # Level 1: jurisdiction_card.json — all jurisdictions on disk
    if level in ("L1", "ALL"):
        print("\n--- Level 1: jurisdiction_card.json ---")
        process_level1_citations(jurisdictions=None, dry_run=dry_run, stats=stats)

    # Level 2: venue_card.json — all venues on disk
    if level in ("L2", "ALL"):
        print("\n--- Level 2: venue_card.json ---")
        process_level2_citations(venues=None, dry_run=dry_run, stats=stats)

    # Level 3: raw files — all venues on disk
    if level in ("L3", "ALL"):
        print("\n--- Level 3: raw files ---")
        process_level3_citations(dry_run=dry_run, stats=stats)

    # Level 4: level4.json — all jurisdictions on disk
    if level in ("L4", "ALL"):
        print("\n--- Level 4: level4.json ---")
        process_level4_citations(jurisdictions=None, dry_run=dry_run, stats=stats)

    print(f"\n=== Catch-up complete ===\n{stats.summary()}")


if __name__ == "__main__":
    main()
