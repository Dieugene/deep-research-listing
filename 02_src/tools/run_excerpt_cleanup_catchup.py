"""
Catch-up script: clean Google snippet artifacts from excerpts in all JSON files.

Removes leading date prefixes ("Mon DD, YYYY -- "), trailing "...Read more",
and mid-text snippet joins.

Idempotent: safe to re-run; files with no artifacts are not modified.

Usage:
    cd D:\\_workspace\\deep-research-listing
    venv\\Scripts\\python.exe 02_src/tools/run_excerpt_cleanup_catchup.py
    venv\\Scripts\\python.exe 02_src/tools/run_excerpt_cleanup_catchup.py --jurisdiction "Россия"
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

from pipeline.excerpt_cleaner import run_excerpt_cleanup  # noqa: E402


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Catch-up: clean Google snippet artifacts from excerpt text. "
            "Removes date prefixes, trailing '...Read more', and mid-text joins."
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
        print(f"Cleaning excerpts for jurisdictions: {jurisdictions} ...")
    else:
        print("Cleaning excerpts for ALL jurisdictions ...")

    run_excerpt_cleanup(jurisdictions=jurisdictions)

    print("Done.")


if __name__ == "__main__":
    main()
