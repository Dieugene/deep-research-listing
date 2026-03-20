"""
Catch-up script: canonical tier mapping for all venue x instrument_class groups.

Reconciles tier structures from 3A, 3B, 3C research queries into a unified
canonical tier map using LLM.

Idempotent: groups that already have a tier_map.json are skipped.

Usage:
    cd D:\\_workspace\\deep-research-listing
    venv\\Scripts\\python.exe 02_src/tools/run_tier_mapping_catchup.py
    venv\\Scripts\\python.exe 02_src/tools/run_tier_mapping_catchup.py --jurisdiction "Германия"
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

from dotenv import load_dotenv  # noqa: E402
load_dotenv(dotenv_path=REPO_ROOT / ".env")

from pipeline.tier_mapper import run_canonical_tier_mapping  # noqa: E402


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Catch-up: canonical tier mapping for L3 data. "
            "Reconciles 3A/3B/3C tier structures into a unified map."
        )
    )
    parser.add_argument(
        "--jurisdiction",
        nargs="+",
        metavar="NAME_RU",
        default=None,
        help=(
            "Limit processing to one or more jurisdictions by their name_ru "
            "(country directory name). If omitted, all jurisdictions are scanned."
        ),
    )
    args = parser.parse_args()

    jurisdictions = args.jurisdiction  # list[str] | None

    if jurisdictions:
        print(f"Running canonical tier mapping for jurisdictions: {jurisdictions} ...")
    else:
        print("Running canonical tier mapping for ALL jurisdictions ...")

    run_canonical_tier_mapping(jurisdictions=jurisdictions)

    print("Done.")


if __name__ == "__main__":
    main()
