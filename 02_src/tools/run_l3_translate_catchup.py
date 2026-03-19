"""
Task 021 catch-up: translate L3 section descriptions to Russian for all existing data.

Adds `description_ru` to every section in 3A_raw.json, 3B_raw.json, 3C_raw.json
across all jurisdictions. Already-translated sections are skipped (idempotent).

Usage:
    cd 02_src
    venv\\Scripts\\python.exe tools/run_l3_translate_catchup.py
    venv\\Scripts\\python.exe tools/run_l3_translate_catchup.py --jurisdictions Великобритания Гонконг
"""
import sys
from pathlib import Path

# Allow running from 02_src/ or project root
_this_file = Path(__file__).resolve()
_src_dir = _this_file.parents[1]  # 02_src/
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

# Load environment variables (.env must contain OPENAI_API_KEY)
from dotenv import load_dotenv
load_dotenv(dotenv_path=_this_file.parents[2] / ".env")

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Translate L3 section descriptions to Russian (catch-up for all existing data)."
    )
    parser.add_argument(
        "--jurisdictions",
        nargs="+",
        metavar="NAME_RU",
        default=None,
        help="Process only these jurisdictions (Russian country-dir names). Default: all.",
    )
    args = parser.parse_args()

    from pipeline.l3_translate import run_l3_translate

    print("Translating L3 section descriptions...")
    run_l3_translate(jurisdictions=args.jurisdictions)
    print("Done.")


if __name__ == "__main__":
    main()
