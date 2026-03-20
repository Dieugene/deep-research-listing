"""
Catch-up script: join fragmented excerpts across all JSON files using LLM.

Detects excerpt lists that look like line-by-line PDF/table fragments
(many short strings) and uses LLM to reconstruct coherent text blocks.

Idempotent: sources with excerpts_joined=true are skipped.

Usage:
    cd D:\\_workspace\\deep-research-listing
    venv\\Scripts\\python.exe 02_src/tools/run_excerpt_joiner_catchup.py
    venv\\Scripts\\python.exe 02_src/tools/run_excerpt_joiner_catchup.py --jurisdiction "Россия"
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

from pipeline.excerpt_joiner import run_excerpt_joiner  # noqa: E402


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Catch-up: join fragmented excerpts using LLM. "
            "Detects line-by-line PDF/table fragments and reconstructs coherent text."
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
        print(f"Joining fragmented excerpts for jurisdictions: {jurisdictions} ...")
    else:
        print("Joining fragmented excerpts for ALL jurisdictions ...")

    run_excerpt_joiner(jurisdictions=jurisdictions)

    print("Done.")


if __name__ == "__main__":
    main()
