"""
Task 020 catch-up: fix "Fetched web page" citation titles for all existing data.
Fetches the real HTML page title for any citation with the placeholder title.
Run manually: python 02_src/tools/run_l3_title_fix_catchup.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.source_classifier import fix_fetched_web_page_titles

if __name__ == "__main__":
    print("Fixing 'Fetched web page' titles...")
    fix_fetched_web_page_titles()
    print("Done.")
