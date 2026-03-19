"""
Task 022: Catchup script — translate all missing _ru fields across all jurisdictions.

Runs all translate_ru_fields functions on the full dataset in 03_data/countries/.

Usage:
    cd 02_src
    venv\\Scripts\\python.exe tools/run_missing_ru_catchup.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.translate_ru_fields import (
    translate_jurisdiction_notes,
    translate_phase2_fields,
    translate_level4_fields,
    normalize_param_ids,
    _get_llm,
)

if __name__ == "__main__":
    llm = _get_llm()

    print("1. Translating jurisdiction notes (notes -> notes_ru)...")
    translate_jurisdiction_notes(llm)

    print("2. Translating Phase 2 fields (tier_ru + ADDITIONAL param labels)...")
    translate_phase2_fields(llm)

    print("3. Normalizing param IDs (Latin P01 -> Cyrillic)...")
    normalize_param_ids()

    print("4. Translating Level 4 fields (reforms + ptools)...")
    translate_level4_fields(llm)

    print("Done.")
