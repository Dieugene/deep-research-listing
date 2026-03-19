"""
Catch-up: build matrix.json for all existing L3 cells that are missing it.

This script is intended as a one-time catch-up to produce matrix.json for all
cells that have 3A_raw.json, 3B_raw.json, and/or 3C_raw.json but no matrix.json.

The process is idempotent — cells that already have matrix.json are skipped.

Steps per cell (skipped if matrix.json already exists):
  1. Algorithmic mapping: 3A/3B/3C -> 4x5 matrix structure
  2. LLM routing: sanctions / monitoring_suspension / additional_findings
  3. Save matrix.json to cell directory

Usage:
    cd 02_src
    venv\\Scripts\\python.exe tools/run_matrix_catchup.py [--dry-run] [--venues VENUE ...]

Options:
    --dry-run        Only log which cells are missing matrix.json, do not run LLM calls.
    --venues KEYS    Space-separated venue_key list to process (default: all venues).
"""

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allow running from 02_src/ or project root
# ---------------------------------------------------------------------------
_this_file = Path(__file__).resolve()
_src_dir = _this_file.parents[1]  # 02_src/
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

_project_root = _this_file.parents[2]
_env_file = _project_root / ".env"
if _env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_env_file)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Catch-up: build matrix.json for all L3 cells missing it."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Only show which cells are missing matrix.json; do not run LLM.",
    )
    parser.add_argument(
        "--venues",
        nargs="+",
        metavar="VENUE_KEY",
        default=None,
        help="Process only these venue_key values (default: all).",
    )
    args = parser.parse_args()

    from pipeline.config import COUNTRIES_DIR
    from pipeline.logging_setup import get_logger
    from pipeline.config import LOGS_DIR
    import datetime

    logger = get_logger(
        "run_matrix_catchup",
        LOGS_DIR / f"matrix_catchup_{datetime.date.today()}.log",
    )

    if args.dry_run:
        # Dry run: just count and list missing matrix.json files
        missing = []
        for country_dir in COUNTRIES_DIR.iterdir():
            if not country_dir.is_dir():
                continue
            l3_dir = country_dir / "level_3"
            if not l3_dir.exists():
                continue
            for venue_dir in l3_dir.iterdir():
                if not venue_dir.is_dir():
                    continue
                if args.venues and venue_dir.name not in args.venues:
                    continue
                for cell_dir in venue_dir.iterdir():
                    if not cell_dir.is_dir():
                        continue
                    if not (cell_dir / "3A_raw.json").exists():
                        continue
                    if not (cell_dir / "matrix.json").exists():
                        missing.append(cell_dir)

        logger.info("DRY RUN: %d cells missing matrix.json", len(missing))
        for cell_dir in missing:
            logger.info("  MISSING: %s", cell_dir)
        return

    # Real run
    from level_3.matrix_builder import build_matrix_all
    logger.info("Starting matrix catch-up (venues filter: %s)", args.venues)
    build_matrix_all(venues=args.venues, llm=None)
    logger.info("Matrix catch-up complete.")


if __name__ == "__main__":
    main()
