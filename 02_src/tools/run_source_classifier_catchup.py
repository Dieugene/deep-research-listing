"""
Task 014 catch-up: classify source types for all existing data.
Run manually: python 02_src/tools/run_source_classifier_catchup.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.source_classifier import process_source_types

if __name__ == "__main__":
    print("Classifying source types...")
    process_source_types()
    print("Done.")
