"""
Task 013 catch-up: generate labels and normalize articulated_by for all existing level4.json.
Run manually: python 02_src/tools/run_l4_labels_catchup.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.level4_postprocess import process_level4_labels, process_level4_articulated_by

if __name__ == "__main__":
    print("Generating L4 labels...")
    process_level4_labels()
    print("Normalizing articulated_by...")
    process_level4_articulated_by()
    print("Done.")
