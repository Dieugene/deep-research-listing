"""
Add citations/sources from Parallel API basis to processed pipeline files.

Thin CLI wrapper — all logic lives in pipeline.sources.

Usage:
    cd D:\\_workspace\\deep-research-listing
    venv\\Scripts\\python.exe tools/add_citations.py [--level L1|L2|L3|L4|ALL] [--dry-run]
"""

import argparse
import io
import sys
from pathlib import Path

# Force UTF-8 output on Windows (avoids cp1251 UnicodeEncodeError for Cyrillic paths)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Bootstrap: add repo src to sys.path so we can import pipeline.sources
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
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

    stats = Stats()
    dry_run = args.dry_run
    level = args.level

    if level in ("L1", "ALL"):
        process_level1_citations(jurisdictions=None, dry_run=dry_run, stats=stats)

    if level in ("L2", "ALL"):
        process_level2_citations(venues=None, dry_run=dry_run, stats=stats)

    if level in ("L3", "ALL"):
        process_level3_citations(dry_run=dry_run, stats=stats)

    if level in ("L4", "ALL"):
        process_level4_citations(jurisdictions=None, dry_run=dry_run, stats=stats)

    print(f"\n=== Done ===\n{stats.summary()}")


if __name__ == "__main__":
    main()
