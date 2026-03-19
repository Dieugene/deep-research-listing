"""
Task 012 catch-up: normalize L1/L2 fields for all existing data.
Run manually: python 02_src/tools/run_l1_l2_normalize_catchup.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from pipeline.l1_l2_normalize import process_l1_normalizations, process_l2_normalizations

if __name__ == "__main__":
    print("Running L1 normalization...")
    process_l1_normalizations()
    print("Running L2 normalization...")
    process_l2_normalizations()
    print("Done.")
