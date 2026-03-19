"""
Task 020 catch-up: classify L3 citation types for all existing data.
Adds type field to all citations[] in 3A/3B/3C_raw.json files.
Run manually: python 02_src/tools/run_l3_citation_types_catchup.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.source_classifier import process_l3_citation_types

if __name__ == "__main__":
    print("Classifying L3 citation types...")
    process_l3_citation_types()
    print("Done.")
